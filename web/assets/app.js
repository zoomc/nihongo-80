/* Nihongo 80 前端逻辑（PC / 手机双端）。
 * 不向任何服务器发送学习数据：不发起网络请求，不读写远程接口。
 * 学习状态真源是本地 SQLite；本页只展示 / 练习 / 即时判分 / 生成 NH80R1 回传码，
 * localStorage 仅用于「当日刷新恢复」缓存，不是状态真源。
 */
(function () {
  'use strict';

  function byId(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = String(text);
    return n;
  }
  function esc(s) {
    return String(s === undefined || s === null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function t(v) { return (v === undefined || v === null) ? '' : String(v); }

  /* 词性 / 题型 / 评估标签中文化（首屏不出现英文黑话）。 */
  var POS_ZH = {
    '名詞': '名词', '代名詞': '代名词', '動詞': '动词', '形容詞': '形容词',
    '助動詞': '助动词', '助詞': '助词', '副詞': '副词', '数詞': '数词',
    '感動詞': '感叹词', '連体詞': '连体词', '接続詞': '接续词',
    '接尾辞': '接尾辞', '接頭辞': '接头辞'
  };
  function zhPos(s) {
    var out = t(s);
    Object.keys(POS_ZH).forEach(function (k) { out = out.split(k).join(POS_ZH[k]); });
    return out;
  }
  var QTYPE_ZH = {
    mcq: '选择题', fill: '填空题', listen: '听写题', read: '阅读题',
    reorder: '排序题', error_correct: '改错题', translate: '翻译题',
    free_production: '自由表达', dialogue: '对话题'
  };
  function qTypeZh(s) { return QTYPE_ZH[t(s)] || (t(s) ? t(s) : '练习题'); }
  var ASSESS_ZH = {
    diagnostic: '摸底（不计分，只用来定起点）', weekly: '每周小测',
    stage: '阶段测', midterm: '中期测', n3_readiness: 'N3 水平摸底',
    final: '结课测', none: '无'
  };
  function assessmentZh(s) { return ASSESS_ZH[t(s)] || t(s); }

  /* 有值才渲染该行；缺失字段一律跳过，页面绝不出现 undefined。 */
  function lineIf(parent, label, value, cls) {
    if (value === undefined || value === null || value === '') return null;
    var p = el('div', 'kv');
    if (label) p.appendChild(el('span', 'kv-k', label));
    p.appendChild(el('span', 'kv-v' + (cls ? ' ' + cls : ''), value));
    parent.appendChild(p);
    return p;
  }

  /* 每个词 / 每句 / 每段旁的「听」入口：用户手势内解锁 + 朗读，自带降级提示节点。 */
  function listenBtn(text, label) {
    var wrap = el('span', 'listen-wrap');
    var b = el('button', 'btn btn-mini listen-btn', label || '听');
    b.type = 'button';
    var notice = el('span', 'inline-notice');
    notice.hidden = true;
    b.addEventListener('click', function () { primeTTS(); speak(text || '', notice); });
    wrap.appendChild(b);
    wrap.appendChild(notice);
    return wrap;
  }

  /* 常显区块（非折叠）：标题 + 一句中文引导。 */
  function sectionPlain(title, hint) {
    var box = el('section', 'block');
    box.appendChild(el('h2', 'block-title', title));
    if (hint) box.appendChild(el('p', 'block-hint', hint));
    return box;
  }
  function readJSON(id) {
    var n = byId(id);
    if (!n) return null;
    try { return JSON.parse(n.textContent); } catch (e) { return null; }
  }
  function pad2(n) { return String(n).padStart(2, '0'); }
  function pad3(n) { return String(n).padStart(3, '0'); }
  /* 与 scripts/learning.py 的 norm_answer() 保持同构（REVISION_CONTRACT §3.2）：
     NFKC 归一 → 去所有空白（含全角空格）→ ，转 , → 去句末 。．.！!？?。
     判分只做「等价形式」归一，不做语义猜测。 */
  function norm(s) {
    var v = String(s === undefined || s === null ? '' : s);
    if (v.normalize) { try { v = v.normalize('NFKC'); } catch (e) {} }
    v = v.replace(/[\s\u3000]+/g, '').replace(/，/g, ',');
    return v.replace(/[。．.！!？?]+$/, '');
  }
  function isWide() {
    try {
      if (typeof window !== 'undefined' && window.matchMedia) {
        return window.matchMedia('(min-width: 900px)').matches;
      }
      if (typeof window !== 'undefined' && window.innerWidth) {
        return window.innerWidth >= 900;
      }
    } catch (e) {}
    return false;
  }

  /* ---------------- 回传码（CONTRACTS 第 10 节） ---------------- */
  function b64urlEncode(str) {
    var bytes = new TextEncoder().encode(str);
    var bin = '';
    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  function localISO() {
    var d = new Date();
    var off = -d.getTimezoneOffset();
    var sign = off >= 0 ? '+' : '-';
    return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate())
      + 'T' + pad2(d.getHours()) + ':' + pad2(d.getMinutes()) + ':' + pad2(d.getSeconds())
      + sign + pad2(Math.floor(Math.abs(off) / 60)) + ':' + pad2(Math.abs(off) % 60);
  }
  function makeSessionId() {
    var d = new Date();
    var date = '' + d.getFullYear() + pad2(d.getMonth() + 1) + pad2(d.getDate());
    var ck = 'nh80:seq:' + date, n = 0;
    try { n = parseInt(localStorage.getItem(ck) || '0', 10) || 0; } catch (e) { n = 0; }
    n += 1;
    try { localStorage.setItem(ck, String(n)); } catch (e) {}
    return 'session-' + date + '-' + String(n).padStart(3, '0');
  }
  function encodeReturnCode(payload) {
    return 'NH80R1.' + b64urlEncode(JSON.stringify(payload));
  }
  function gradeAnswer(q, ans) {
    if (q.type === 'free_production' || q.type === 'dialogue') return null;
    if (q.answer === undefined || q.answer === null || String(q.answer).length === 0) return null;
    return norm(ans) === norm(q.answer);
  }
  function makePayload(state) {
    var results = Object.keys(state.results).map(function (qid) {
      var r = state.results[qid];
      /* 已揭示答案 = 放弃独立回忆；hinted 只能上调，不能被前端回退（契约 §3.1）。 */
      var revealed = !!r.revealed_before_submit;
      var o = {
        qid: r.qid, answer: r.answer, correct: !!r.correct,
        hinted: !!(r.hinted || revealed),
        revealed_before_submit: revealed,
        pre_reveal_answer: (r.pre_reveal_answer === undefined || r.pre_reveal_answer === null)
          ? '' : String(r.pre_reveal_answer),
        seconds: Math.max(0, Math.round(r.seconds || 0)), error_type: r.error_type || null
      };
      if (revealed && r.revealed_at) o.revealed_at = r.revealed_at;
      /* 开放题自评写独立字段，绝不冒充 correct / 掌握判定（REDESIGN §5、P0-9）。 */
      if (r.self_assessed) o.self_assessed = r.self_assessed;
      return o;
    });
    var total = results.reduce(function (a, r) { return a + r.seconds; }, 0);
    /* 复习三档自评单独成数组，绝不写进 results[].correct（REDESIGN §4.3 / §5）。
       import-web-result 只读取它认识的字段，新增顶层字段完全向后兼容。 */
    var rr = state.reviewRatings || {};
    var review_ratings = Object.keys(rr).map(function (kid) {
      return { kid: kid, rating: rr[kid] };
    });
    return {
      v: 1, day: state.day, session: state.session, ts: localISO(),
      results: results, minutes: Math.max(1, Math.round(total / 60)), source: 'web',
      review_ratings: review_ratings
    };
  }


  /* 可选云端同步：只发原始作答事件，不发 correct；失败静默，回传码仍是唯一兜底。
     服务端（Worker）会用 answer-key.json 重新判分，网页永远不是判分权威。 */
  function autoSync(payload) {
    try {
      if (typeof fetch !== 'function' || typeof location === 'undefined') return;
      if (location.protocol !== 'http:' && location.protocol !== 'https:') return;
      if (typeof navigator !== 'undefined' && navigator.onLine === false) return;
      if (!payload || (!(payload.results || []).length && !(payload.review_ratings || []).length)) return;
      var body = JSON.stringify({
        v: 1, day: payload.day, session: payload.session, minutes: payload.minutes,
        client_ts: payload.ts,
        results: (payload.results || []).map(function (r) {
          return { qid: r.qid, answer: r.answer, hinted: !!r.hinted,
                   revealed_before_submit: !!r.revealed_before_submit, seconds: r.seconds || 0 };
        })
      });
      fetch('/api/events', { method: 'POST', headers: { 'content-type': 'application/json' },
                             body: body, keepalive: true })
        .then(function (res) { globalThis.NH80.lastSync = res && res.ok ? 'ok' : 'skipped'; })
        .catch(function () { globalThis.NH80.lastSync = 'offline'; });
    } catch (e) { /* 同步不是学习的前置条件，任何异常都不影响回传码 */ }
  }

  /* 暴露纯函数 + 调试快照，便于在 Node 中做回传码与布局自测（不影响浏览器运行）。 */
  globalThis.NH80 = {
    b64urlEncode: b64urlEncode,
    encodeReturnCode: encodeReturnCode,
    gradeAnswer: gradeAnswer,
    makePayload: makePayload,
    norm: norm,
    debug: function () {
      return {
        mode: (typeof LAYOUT !== 'undefined' && LAYOUT) ? LAYOUT.mode : null,
        hasQuiz: !!QUIZ,
        answered: QUIZ ? Object.keys(QUIZ.state.results).length : 0,
        total: QUIZ ? QUIZ.total : 0,
        code: QUIZ ? QUIZ.lastCode : null
      };
    }
  };

  if (typeof document === 'undefined' || !document.addEventListener) return;
  /* 入口调用置于 IIFE 最末尾，确保下方 var 顶层状态已初始化后再 init()。 */

  /* ---------------- 全局状态 ---------------- */
  var LAYOUT = { wide: false, mode: 'step' };   // step=手机一屏一题 / grid=PC 一屏多题
  var TTS = { supported: false, jaVoice: false, muted: false, rate: 0.9, unlocked: false, lastText: '' };
  var QUIZ = null;                              // 练习控制器，供外壳按钮调用
  var TEACHER_BOX = null;                       // 页尾折叠「给老师/系统」容器，完成回传码时打开

  /* ---------------- 语音：手势解锁 + 播放/停止/语速 + 降级 ---------------- */
  function refreshVoices() {
    if (!TTS.supported) { TTS.jaVoice = false; return; }
    var vs = [];
    try { vs = speechSynthesis.getVoices() || []; } catch (e) { vs = []; }
    TTS.jaVoice = vs.some(function (v) { return v && v.lang && /^ja/i.test(v.lang); });
  }
  function detectTTS() {
    TTS.supported = (typeof window !== 'undefined') && ('speechSynthesis' in window)
      && (typeof SpeechSynthesisUtterance !== 'undefined');
    refreshVoices();
    if (TTS.supported && typeof speechSynthesis !== 'undefined') {
      try { speechSynthesis.addEventListener('voiceschanged', refreshVoices); } catch (e) {}
    }
  }
  function showTTSNotice(node, msg) {
    if (!node) return;
    node.textContent = msg;
    node.hidden = false;
  }
  /* iOS / Android：speechSynthesis 首次必须在用户手势里 speak 一次来解锁语音队列。
     所有 speak 调用本身都发生在 click 处理器内；这里额外提供显式「试听/解锁」手势。 */
  function primeTTS() {
    if (TTS.unlocked || !TTS.supported) return;
    try {
      var u = new SpeechSynthesisUtterance('');
      u.lang = 'ja-JP'; u.volume = 0; u.rate = 1;
      speechSynthesis.speak(u);
      TTS.unlocked = true;
    } catch (e) {}
  }
  function speak(text, noticeNode) {
    if (!text) return;
    TTS.lastText = String(text);
    if (TTS.muted) { showTTSNotice(noticeNode, '静音学习已开启：仅显示文本与假名读音。'); return; }
    if (!TTS.supported) {
      showTTSNotice(noticeNode, '当前浏览器不支持语音合成，已显示文本与假名读音，请跟读 / 静音学习。');
      return;
    }
    primeTTS();  // 必须在用户手势内
    if (!TTS.jaVoice) {
      showTTSNotice(noticeNode, '未检测到日语语音（ja-JP）：可能发音不准或无声；已显示假名读音，请跟读或开启静音学习。');
    }
    try {
      speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(String(text));
      u.lang = 'ja-JP';
      u.rate = TTS.rate;
      if (TTS.jaVoice) {
        var vs = speechSynthesis.getVoices() || [];
        for (var i = 0; i < vs.length; i++) {
          if (vs[i] && vs[i].lang && /^ja/i.test(vs[i].lang)) { u.voice = vs[i]; break; }
        }
      }
      u.onerror = function () {
        showTTSNotice(noticeNode, '语音播放被系统拒绝 / 失败：已显示文本与假名读音，请跟读或静音学习。');
      };
      speechSynthesis.speak(u);
    } catch (e) {
      showTTSNotice(noticeNode, '语音播放失败：已显示文本与假名读音，请跟读或静音学习。');
    }
  }
  function stopSpeak() {
    try { speechSynthesis.cancel(); } catch (e) {}
  }
  function setupTTSBanner() {
    detectTTS();
    document.body.classList.toggle('no-ja-tts', !TTS.supported || !TTS.jaVoice);
    var b = byId('tts-banner');
    var side = byId('side-tts');
    var msg;
    if (!TTS.supported) {
      msg = '语音能力检测：浏览器不支持 speechSynthesis。已降级为「文本 + 假名读音」，可跟读或静音学习；不依赖任何外部 TTS。';
    } else if (!TTS.jaVoice) {
      msg = '语音能力检测：支持语音合成，但未发现日语语音（ja-JP）。发音可能不准或无声；已显示假名读音，可手动播放或静音学习。';
    } else {
      msg = '语音能力检测：已发现日语语音（ja-JP）。首次播放请在下方点「试听 / 解锁语音」（iOS / Android 需用户手势解锁）。';
    }
    if (b) {
      b.textContent = msg;
      var bar = el('div', 'tts-controls');
      var unlock = el('button', 'btn btn-mini', '试听 / 解锁语音');
      unlock.type = 'button';
      unlock.addEventListener('click', function () { primeTTS(); speak(TTS.lastText || 'こんにちは'); });
      var stop = el('button', 'btn btn-mini', '停止朗读');
      stop.type = 'button';
      stop.addEventListener('click', function () { stopSpeak(); });
      var rate = el('select', 'rate-sel');
      [['0.7', '慢 0.7'], ['0.9', '标准 0.9'], ['1.0', '快 1.0']].forEach(function (o) {
        var op = el('option', '', o[1]); op.value = o[0]; rate.appendChild(op);
      });
      rate.value = String(TTS.rate);
      rate.setAttribute('aria-label', '朗读语速');
      rate.addEventListener('change', function () {
        TTS.rate = parseFloat(rate.value) || 0.9;
        if (TTS.lastText) speak(TTS.lastText);
      });
      var mute = el('button', 'btn btn-mini', TTS.muted ? '关闭静音' : '静音学习');
      mute.type = 'button';
      mute.addEventListener('click', function () {
        TTS.muted = !TTS.muted;
        mute.textContent = TTS.muted ? '关闭静音' : '静音学习';
        if (TTS.muted) stopSpeak();
      });
      bar.appendChild(unlock); bar.appendChild(stop); bar.appendChild(rate); bar.appendChild(mute);
      b.appendChild(bar);
      b.hidden = false;
    }
    if (side) {
      side.textContent = TTS.jaVoice
        ? '发音：点句子旁的「听」跟读一遍。'
        : '发音：这台设备没有日语语音，看假名跟读即可，不影响今天的学习。';
    }
  }

  /* ---------------- 外壳：布局 / 进度 / 在线状态 / 侧栏导航 ---------------- */
  function detectLayout() {
    LAYOUT.wide = isWide();
    LAYOUT.mode = LAYOUT.wide ? 'grid' : 'step';
    document.body.classList.toggle('is-wide', LAYOUT.wide);
    document.body.classList.toggle('is-narrow', !LAYOUT.wide);
  }
  function setProgress(done, total, label, sub) {
    var pct = total ? Math.round((done / total) * 100) : 0;
    var bar = byId('top-progress-bar');
    if (bar) bar.style.width = pct + '%';
    var tp = byId('top-progress');
    if (tp && tp.setAttribute) tp.setAttribute('aria-valuenow', String(pct));
    var sp = byId('side-progress');
    if (sp) sp.textContent = label || ('已答 ' + done + ' / ' + total + ' 题');
    var as = byId('appbar-sub');
    if (as && sub) as.textContent = sub;
  }
  function setOnlineStatus() {
    var box = byId('side-offline');
    var online = (typeof navigator !== 'undefined' && 'onLine' in navigator) ? navigator.onLine : true;
    if (box) {
      box.textContent = online
        ? '离线也能看今天的内容；做完的练习记得带回 WorkBuddy 会话。'
        : '当前离线：内容已缓存，练习结果稍后带回 WorkBuddy 会话。';
    }
    document.body.classList.toggle('is-offline', !online);
  }
  function doAction(act) {
    if (!QUIZ) return;
    if (act === 'prev') QUIZ.prev();
    else if (act === 'next') QUIZ.next();
    else if (act === 'submit') QUIZ.submit();
    else if (act === 'finish') QUIZ.finish();
    else if (act === 'copy') QUIZ.copy();
  }
  function setupChrome() {
    var toggle = byId('toc-toggle');
    var sidebar = byId('sidebar');
    if (toggle && sidebar) {
      toggle.addEventListener('click', function () {
        var open = sidebar.classList.toggle('open');
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        toggle.textContent = open ? '收起' : '目录';
      });
      sidebar.addEventListener('click', function (e) {
        if (e.target && e.target.tagName === 'A') {
          sidebar.classList.remove('open');
          toggle.setAttribute('aria-expanded', 'false');
          toggle.textContent = '目录';
        }
      });
    }
    var actionbar = byId('actionbar');
    if (actionbar && actionbar.children) {
      Array.prototype.forEach.call(actionbar.children, function (btn) {
        var act = btn.getAttribute && btn.getAttribute('data-act');
        if (act) btn.addEventListener('click', function () { doAction(act); });
      });
    }
    if (typeof window !== 'undefined' && window.addEventListener) {
      try {
        window.addEventListener('online', setOnlineStatus);
        window.addEventListener('offline', setOnlineStatus);
      } catch (e) {}
    }
    setOnlineStatus();
  }
  function renderNav(site, day) {
    var nav = byId('side-nav');
    var as = byId('appbar-sub');
    if (!day) {
      if (as) as.textContent = '每日学习 · 目录';
      if (nav) {
        var home = el('a', 'nav-link', '目录首页');
        home.href = 'index.html';
        nav.appendChild(home);
      }
      return;
    }
    var d = day.day;
    var total = (site && site.meta && site.meta.days)
      ? site.meta.days : (site && site.days ? site.days.length : 80);
    if (as) as.textContent = '第 ' + d + ' 天 · ' + (day.phase || '') + ' · ' + (day.theme || '');
    if (!nav) return;
    var prev = el('a', 'nav-link', '前一天');
    prev.href = d > 1 ? 'day-' + pad3(d - 1) + '.html' : 'index.html';
    var home2 = el('a', 'nav-link', '目录');
    home2.href = 'index.html';
    var next = el('a', 'nav-link', '后一天');
    next.href = d < total ? 'day-' + pad3(d + 1) + '.html' : 'index.html';
    nav.appendChild(prev); nav.appendChild(home2); nav.appendChild(next);
    var jump = el('a', 'nav-link', '跳到练习');
    jump.href = '#app';
    nav.appendChild(jump);
  }

  /* ---------------- 通用渲染 ---------------- */
  function section(title, open) {
    var d = el('details', 'section');
    if (open) d.open = true;
    d.appendChild(el('summary', 'section-sum', title));
    var body = el('div', 'section-body');
    d.appendChild(body);
    d._body = body;
    return d;
  }
  var PHASE_COLORS = {
    P1: '#bcd7ff', P2: '#a9e6c3', P3: '#ffe1a1',
    P4: '#ffc7bb', P5: '#dcc8ff', P6: '#d3dae2'
  };
  var BLOCK_COLORS = {
    review: '#8fb8ff', input: '#8fd9ad', practice: '#ffd27a',
    output: '#f4a7a0', drill: '#c9b3f5', assessment: '#e59ad6'
  };
  function phaseColor(p) { return PHASE_COLORS[p] || '#e6e9ed'; }
  function shade(hex, f) {
    var c = hex.replace('#', '');
    var r = parseInt(c.substring(0, 2), 16),
        g = parseInt(c.substring(2, 4), 16),
        b = parseInt(c.substring(4, 6), 16);
    f = Math.max(0, Math.min(1, f));
    return 'rgb(' + Math.round(255 + (r - 255) * f) + ','
      + Math.round(255 + (g - 255) * f) + ',' + Math.round(255 + (b - 255) * f) + ')';
  }
  function phaseLegend() {
    var box = el('div', 'legend');
    Object.keys(PHASE_COLORS).forEach(function (p) {
      var it = el('span', 'legend-item');
      var sw = el('span', 'legend-swatch');
      sw.style.background = PHASE_COLORS[p];
      it.appendChild(sw);
      it.appendChild(document.createTextNode(p));
      box.appendChild(it);
    });
    return box;
  }
  function vizCard(title, markup, extra) {
    var c = el('div', 'viz-card' + (extra ? ' ' + extra : ''));
    c.appendChild(el('h3', 'viz-title', title));
    var sc = el('div', 'viz-scroll');
    var m = el('div', 'svg-mount');
    m.innerHTML = markup;        // HTML5 自动进入 SVG 命名空间，无需外部 xmlns
    sc.appendChild(m);
    c.appendChild(sc);
    return c;
  }
  function heatmapSVG(site, currentDay) {
    var s = site || { days: [], meta: {} };
    var total = (s.meta && s.meta.days) ? s.meta.days : (s.days ? s.days.length : 80);
    var map = {};
    (s.days || []).forEach(function (x) { map[x.day] = x; });
    var cols = 10, cell = 26, gap = 5, pad = 8;
    var rows = Math.ceil(total / cols);
    var w = pad * 2 + cols * (cell + gap);
    var h = pad * 2 + rows * (cell + gap);
    var maxQ = 1;
    (s.days || []).forEach(function (x) { if ((x.question_count || 0) > maxQ) maxQ = x.question_count; });
    var out = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="80 天课程结构热力图">';
    for (var i = 0; i < total; i++) {
      var day = i + 1;
      var col = i % cols, row = Math.floor(i / cols);
      var x = pad + col * (cell + gap), y = pad + row * (cell + gap);
      var info = map[day];
      var fill = '#dfe4ea', stroke = '#c3ccd6', sw = 1;
      var title = 'D' + pad3(day) + '（待生成）';
      if (info) {
        var ratio = (info.question_count || 0) / maxQ;
        fill = shade(phaseColor(info.phase), 0.15 + 0.55 * ratio);
        stroke = '#9aa4b0';
        title = 'D' + pad3(day) + ' · ' + (info.phase || '') + ' · ' + (info.theme || '')
          + ' · 题 ' + (info.question_count || 0) + ' / 新 ' + (info.new_count || 0);
      }
      if (currentDay === day) { stroke = '#1f6feb'; sw = 3; }
      out += '<a href="day-' + pad3(day) + '.html"><rect x="' + x + '" y="' + y
        + '" width="' + cell + '" height="' + cell + '" rx="4" fill="' + fill
        + '" stroke="' + stroke + '" stroke-width="' + sw + '"><title>' + esc(title)
        + '</title></rect></a>';
    }
    out += '</svg>';
    return out;
  }
  function dayStructureSVG(day) {
    var items = [
      ['词汇', (day.vocab || []).length], ['语法', (day.grammar || []).length],
      ['汉字', (day.kanji || []).length], ['题目', (day.questions || []).length],
      ['素材', (day.materials || []).length]
    ];
    var w = 300, rowH = 30, pad = 8, labelW = 48, barMax = 200;
    var h = pad * 2 + items.length * rowH, max = 1;
    items.forEach(function (it) { if (it[1] > max) max = it[1]; });
    var out = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="当日结构">';
    items.forEach(function (it, i) {
      var y = pad + i * rowH, bw = Math.round((it[1] / max) * barMax);
      out += '<text class="svg-lbl" x="' + pad + '" y="' + (y + 18) + '" font-size="12">' + esc(it[0]) + '</text>'
        + '<rect class="svg-bar-track" x="' + (pad + labelW) + '" y="' + (y + 4) + '" width="' + barMax + '" height="16" rx="3"/>'
        + '<rect class="svg-bar-accent" x="' + (pad + labelW) + '" y="' + (y + 4) + '" width="' + bw + '" height="16" rx="3"/>'
        + '<text class="svg-val" x="' + (pad + labelW + barMax + 6) + '" y="' + (y + 18) + '" font-size="12">' + it[1] + '</text>';
    });
    out += '</svg>';
    return out;
  }
  function typeDistSVG(questions) {
    var counts = {};
    (questions || []).forEach(function (q) { counts[q.type] = (counts[q.type] || 0) + 1; });
    var keys = Object.keys(counts), max = 1;
    keys.forEach(function (k) { if (counts[k] > max) max = counts[k]; });
    var w = 300, rowH = 28, pad = 8, labelW = 92, barMax = 170;
    var h = pad * 2 + Math.max(1, keys.length) * rowH;
    var out = '<svg viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="题型分布">';
    if (!keys.length) {
      out += '<text class="svg-lbl" x="' + pad + '" y="' + (pad + 16) + '" font-size="12">（无题目）</text>';
    }
    keys.forEach(function (k, i) {
      var y = pad + i * rowH, bw = Math.round((counts[k] / max) * barMax);
      out += '<text class="svg-lbl" x="' + pad + '" y="' + (y + 17) + '" font-size="12">' + esc(k) + '</text>'
        + '<rect class="svg-bar-track" x="' + (pad + labelW) + '" y="' + (y + 4) + '" width="' + barMax + '" height="14" rx="3"/>'
        + '<rect class="svg-bar-good" x="' + (pad + labelW) + '" y="' + (y + 4) + '" width="' + bw + '" height="14" rx="3"/>'
        + '<text class="svg-val" x="' + (pad + labelW + barMax + 6) + '" y="' + (y + 17) + '" font-size="12">' + counts[k] + '</text>';
    });
    out += '</svg>';
    return out;
  }
  function timeBar(blocks, minutes) {
    var total = 0;
    (blocks || []).forEach(function (b) { total += (b.min || 0); });
    if (!total) total = minutes || 60;
    var wrap = el('div', 'timeline-wrap');
    var bar = el('div', 'timeline');
    (blocks || []).forEach(function (b) {
      var seg = el('div', 'timeline-seg');
      seg.style.width = (((b.min || 0) / total) * 100) + '%';
      seg.style.background = BLOCK_COLORS[b.type] || '#cdd6e0';
      seg.title = (b.type || '') + ' · ' + (b.min || 0) + ' 分 · ' + (b.desc || '');
      seg.appendChild(el('span', 'timeline-lbl', (b.min || 0) + '分'));
      bar.appendChild(seg);
    });
    wrap.appendChild(bar);
    var legend = el('div', 'timeline-legend');
    (blocks || []).forEach(function (b) {
      var it = el('span', 'tl-item');
      var sw = el('span', 'tl-swatch');
      sw.style.background = BLOCK_COLORS[b.type] || '#cdd6e0';
      it.appendChild(sw);
      it.appendChild(document.createTextNode((b.type || '') + ' ' + (b.min || 0) + '分 ' + (b.desc || '')));
      legend.appendChild(it);
    });
    wrap.appendChild(legend);
    return wrap;
  }

  /* ---------------- 翻面卡 / 素材 ---------------- */
  function line(parent, label, value) {
    var p = el('div', 'kv');
    if (label) p.appendChild(el('span', 'kv-k', label));
    p.appendChild(el('span', 'kv-v', value === undefined || value === null || value === '' ? '—' : value));
    parent.appendChild(p);
  }
  function toggleReveal(c) {
    var parent = c.parentNode;
    var solo = parent && parent.getAttribute && parent.getAttribute('data-solo') === '1';
    var willReveal = !c.classList.contains('revealed');
    if (willReveal && solo && parent && parent.children) {
      Array.prototype.forEach.call(parent.children, function (sib) {
        if (sib !== c && sib.classList && sib.classList.contains('revealed')) {
          sib.classList.remove('revealed');
        }
      });
    }
    c.classList.toggle('revealed');
  }
  function flipCard(frontText, backBuilder, speakText) {
    var c = el('div', 'flipcard');
    var f = el('button', 'flip-front', frontText);
    f.type = 'button';
    var b = el('div', 'flip-back');
    backBuilder(b);
    if (speakText) {
      var s = el('button', 'btn btn-mini speak-btn', '朗读');
      s.type = 'button';
      s.addEventListener('click', function (e) { e.stopPropagation(); primeTTS(); speak(speakText, null); });
      b.appendChild(s);
    }
    c.appendChild(f); c.appendChild(b);
    f.addEventListener('click', function () { toggleReveal(c); });
    b.addEventListener('click', function (e) { if (!e.target || e.target.tagName !== 'BUTTON') toggleReveal(c); });
    return c;
  }
  function cardGrid(items, builder, solo) {
    var grid = el('div', 'card-grid');
    if (solo) grid.setAttribute('data-solo', '1');
    items.forEach(function (it) { grid.appendChild(builder(it)); });
    return grid;
  }
  function vocabCard(v) {
    var c = flipCard(v.surface || v.id, function (b) {
      line(b, '假名', v.kana);
      line(b, '释义', v.meaning_zh);
      line(b, 'JLPT', v.jlpt);
      line(b, 'ID', v.id);
      b.appendChild(el('div', 'kana-line', '读音：' + (v.kana || '（无）')));
    }, v.surface || v.kana);
    var fk = el('span', 'front-kana', v.kana || '');
    c.querySelector('.flip-front').appendChild(fk);
    return c;
  }
  function grammarCard(g) {
    return flipCard(g.pattern || g.id, function (b) {
      line(b, '含义', g.meaning_zh);
      line(b, '接续', g.connection);
      line(b, '例句', g.example);
      line(b, 'ID', g.id);
    }, g.example || g.pattern);
  }
  function kanjiCard(k) {
    return flipCard(k.char || k.id, function (b) {
      line(b, '音读', (k.onyomi || []).join(' / '));
      line(b, '训读', (k.kunyomi || []).join(' / '));
      b.appendChild(el('div', 'trap', '中日差异：' + (k.zh_trap || '（无）')));
      line(b, 'ID', k.id);
    }, k.char);
  }
  function collapsibleText(text) {
    if (!text) return el('p', 'muted', '（无正文）');
    var limit = 90;
    if (text.length <= limit) return el('p', 'ja-text', text);
    var box = el('div', 'longtext');
    var preview = el('p', 'ja-text', text.slice(0, limit) + '…');
    var full = el('p', 'ja-text', text);
    full.hidden = true;
    var btn = el('button', 'btn btn-mini', '展开全文');
    btn.type = 'button';
    btn.addEventListener('click', function () {
      var showing = !full.hidden;
      full.hidden = showing;
      preview.hidden = !showing;
      btn.textContent = showing ? '展开全文' : '收起';
    });
    box.appendChild(preview); box.appendChild(full); box.appendChild(btn);
    return box;
  }
  function materialCard(m) {
    var c = el('div', 'material');
    c.appendChild(el('h4', 'material-title', (m.kind || '') + ' · ' + (m.title || m.id)));
    if (m.text_ja) {
      c.appendChild(collapsibleText(m.text_ja));
    } else if (m.url) {
      var a = el('a', 'ext-link', m.url);
      a.href = m.url; a.target = '_blank'; a.rel = 'noopener noreferrer';
      var p = el('p', 'muted', '正文为外部索引（版权原因仅链接）：');
      p.appendChild(a); c.appendChild(p);
    } else {
      c.appendChild(el('p', 'muted', '（无正文）'));
    }
    c.appendChild(el('div', 'muted', '许可：' + (m.license || '—') + ' · ID：' + m.id));
    if (m.audio_text) {
      var row = el('div', 'material-actions');
      var play = el('button', 'btn btn-mini', '朗读 / 播放');
      play.type = 'button';
      var stop = el('button', 'btn btn-mini', '停止');
      stop.type = 'button';
      var notice = el('div', 'inline-notice');
      notice.hidden = true;
      play.addEventListener('click', function () { primeTTS(); speak(m.audio_text, notice); });
      stop.addEventListener('click', function () { stopSpeak(); });
      row.appendChild(play); row.appendChild(stop);
      if (m.kind === 'listening') row.appendChild(el('span', 'muted', '听力素材：可反复播放，或静音跟读文本'));
      c.appendChild(row);
      c.appendChild(notice);
      /* 无 ja-JP 语音或不支持时，明确给出可读文本 / 假名，不静默失败。 */
      c.appendChild(el('div', 'kana-line', '文本读音（TTS 降级/对照）：' + m.audio_text));
    }
    return c;
  }

  /* ---------------- 练习输入 ---------------- */
  function buildInput(q, wrap, initial) {
    var opts = q.options || [];
    if (q.type === 'reorder') {
      var chunks = opts.slice(), seq = [];
      var chips = el('div', 'chips');
      var answerLine = el('div', 'reorder-answer', '（按顺序点击词块）');
      var reset = el('button', 'btn btn-mini', '重置');
      reset.type = 'button';
      function refresh() {
        answerLine.textContent = seq.length
          ? seq.map(function (n) { return chunks[n - 1]; }).join(' ') : '（按顺序点击词块）';
      }
      function restore(v) {
        seq = [];
        Array.prototype.forEach.call(chips.children, function (b) { b.disabled = false; b.classList.remove('used'); });
        String(v || '').split(/[,，\s]+/).forEach(function (x) {
          var n = parseInt(x, 10);
          if (n >= 1 && n <= chunks.length) {
            seq.push(n);
            var btn = chips.children[n - 1];
            if (btn) { btn.disabled = true; btn.classList.add('used'); }
          }
        });
        refresh();
      }
      chunks.forEach(function (ch, idx) {
        var b = el('button', 'chip', ch);
        b.type = 'button';
        b.addEventListener('click', function () {
          if (b.disabled) return;
          seq.push(idx + 1); b.disabled = true; b.classList.add('used'); refresh();
        });
        chips.appendChild(b);
      });
      reset.addEventListener('click', function () { restore(''); });
      wrap.appendChild(chips);
      wrap.appendChild(el('div', 'muted', '你的排列：'));
      wrap.appendChild(answerLine);
      wrap.appendChild(reset);
      wrap._getValue = function () { return seq.join(','); };
      wrap._setValue = restore;
      restore(initial);
      return;
    }
    if (opts.length && (q.type === 'mcq' || q.type === 'read' || q.type === 'listen')) {
      var grp = el('div', 'opts'), chosen = String(initial || ''), buttons = [];
      opts.forEach(function (o) {
        var b = el('button', 'opt', o);
        b.type = 'button';
        if (String(o) === chosen) b.classList.add('sel');
        b.addEventListener('click', function () {
          buttons.forEach(function (x) { x.classList.remove('sel'); });
          b.classList.add('sel'); chosen = String(o);
        });
        buttons.push(b); grp.appendChild(b);
      });
      wrap.appendChild(grp);
      wrap._getValue = function () { return chosen; };
      wrap._setValue = function (v) {
        chosen = String(v || '');
        buttons.forEach(function (b) { b.classList.toggle('sel', b.textContent === chosen); });
      };
      return;
    }
    var ta = el('textarea', 'q-text');
    ta.rows = (q.type === 'free_production' || q.type === 'dialogue') ? 4 : 2;
    ta.placeholder = q.type === 'listen' ? '听写你听到的内容…' : '在此作答…';
    ta.value = String(initial || '');
    ta.setAttribute('aria-label', '作答输入框');
    wrap.appendChild(ta);
    wrap._getValue = function () { return ta.value; };
    wrap._setValue = function (v) { ta.value = String(v || ''); };
  }
  function hintText(q) {
    if (q.rubric) return '评分要点：' + q.rubric.replace(/\n+/g, ' ');
    if (q.answer) {
      var a = String(q.answer);
      return '提示：答案共 ' + Array.from(a).length + ' 个字符，开头是「' + a.charAt(0) + '」。';
    }
    if (q.audio_text) return '提示：可反复点击「朗读题目」，注意听写假名。';
    return '提示：先回忆当天词汇 / 语法，再作答。';
  }

  /* 揭示答案 / 提示都属于「放弃独立回忆」，只允许向上写，不允许回退（契约 §3.1）。 */
  var REVEAL_NOTICE = '本次为提示学习，不计为独立回忆';
  var REVEAL_SUBMIT_LABEL = '提交（已看答案，记为提示学习）';

  function markRevealed(r, preAnswer, full) {
    r.hinted = true;
    if (full) r.revealed_before_submit = true;
    if (!r.revealed_at) r.revealed_at = Date.now();
    if (r.pre_reveal_answer === undefined || r.pre_reveal_answer === null) {
      r.pre_reveal_answer = String(preAnswer === undefined || preAnswer === null ? '' : preAnswer);
    }
    return r;
  }
  function revealNoticeNode() {
    return el('div', 'reveal-notice', REVEAL_NOTICE);
  }

  /* ---------------- 练习 + 回传码 ---------------- */
  function buildPractice(day) {
    var qs = day.questions || [];
    var state = { day: day.day, index: 0, session: null, results: {}, started: {} };
    var mode = LAYOUT.mode;

    var sec = section('练习与测验（先作答，再揭示答案与解析）', true);
    sec._body.appendChild(el('p', 'muted',
      mode === 'step'
        ? '手机端一屏一题：用底部「上一题 / 下一题 / 提交」操作，顶部进度条显示进度。'
        : 'PC 端一屏多题：点击题头展开作答，每题独立判分与解析。'));

    var root = el('div', 'quiz quiz-' + mode);
    sec._body.appendChild(root);

    /* 当日恢复：localStorage 只是刷新/断网缓存，不是状态真源 */
    var saved = null;
    try { saved = JSON.parse(localStorage.getItem('nh80:day:' + day.day) || 'null'); } catch (e) { saved = null; }
    if (saved && saved.results) {
      state.results = saved.results;
      state.session = saved.session || null;
      var rb = el('div', 'banner banner-info',
        '已恢复本机当日缓存（仅用于刷新 / 断网恢复，不是学习状态真源，也不代表已完成）。');
      var clr = el('button', 'btn btn-mini', '清除缓存');
      clr.type = 'button';
      clr.addEventListener('click', function () {
        try { localStorage.removeItem('nh80:day:' + day.day); } catch (e) {}
        if (typeof location !== 'undefined' && location.reload) location.reload();
      });
      rb.appendChild(document.createTextNode(' '));
      rb.appendChild(clr);
      root.appendChild(rb);
    }
    if (!state.session) state.session = makeSessionId();

    /* PC 工具条 */
    var toolbar = el('div', 'quiz-toolbar');
    var tbProgress = el('span', 'tb-progress', '已答 0 / ' + qs.length + ' 题');
    var tbFinish = el('button', 'btn btn-primary', '完成并生成回传码');
    tbFinish.type = 'button';
    var tbCopy = el('button', 'btn', '复制回传码');
    tbCopy.type = 'button';
    toolbar.appendChild(tbProgress); toolbar.appendChild(tbFinish); toolbar.appendChild(tbCopy);
    root.appendChild(toolbar);

    /* 回传码面板 */
    var returnBox = el('details', 'return-box');
    returnBox.appendChild(el('summary', 'section-sum', '回传码（NH80R1 · 复制 / 分享 / 下载）'));
    var rbBody = el('div', 'section-body');
    rbBody.appendChild(el('div', 'return-hint',
      '复制后到 WorkBuddy 会话粘贴导入，或先存备忘录稍后导入。由本地 import-web-result 校验、去重、写入 SQLite 并触发 FSRS 排期。网页不写状态、不发送学习数据。'));
    var summary = el('div', 'return-summary', '尚未生成');
    rbBody.appendChild(summary);
    var codeArea = el('textarea', 'code-area');
    codeArea.readOnly = true; codeArea.rows = 4;
    codeArea.setAttribute('aria-label', '回传码文本框（可全选复制）');
    rbBody.appendChild(codeArea);
    var btnRow = el('div', 'btn-row');
    var copyBtn = el('button', 'btn btn-primary', '复制回传码');
    copyBtn.type = 'button';
    var selectBtn = el('button', 'btn', '全选文本');
    selectBtn.type = 'button';
    var shareBtn = el('button', 'btn', '系统分享');
    shareBtn.type = 'button';
    var dlBtn = el('button', 'btn', '下载 .txt');
    dlBtn.type = 'button';
    var regenBtn = el('button', 'btn', '重新生成');
    regenBtn.type = 'button';
    [copyBtn, selectBtn, shareBtn, dlBtn, regenBtn].forEach(function (b) { btnRow.appendChild(b); });
    rbBody.appendChild(btnRow);
    var copyStatus = el('div', 'copy-status', '');
    rbBody.appendChild(copyStatus);
    returnBox.appendChild(rbBody);
    root.appendChild(returnBox);

    var lastCode = '';

    function save() {
      try {
        localStorage.setItem('nh80:day:' + day.day,
          JSON.stringify({ session: state.session, results: state.results }));
      } catch (e) {}
    }
    function elapsed(qid) {
      if (!state.started[qid]) state.started[qid] = Date.now();
      return Math.round((Date.now() - state.started[qid]) / 1000);
    }
    function generate(open) {
      var payload = makePayload(state);
      autoSync(payload);
      lastCode = encodeReturnCode(payload);
      QUIZ.lastCode = lastCode;
      codeArea.value = lastCode;
      summary.textContent = '已答 ' + payload.results.length + ' / ' + qs.length
        + ' 题 · 约 ' + payload.minutes + ' 分钟 · 会话 ' + payload.session
        + ' · 来源 ' + payload.source;
      if (open) returnBox.open = true;
      return lastCode;
    }
    function selectCode() {
      codeArea.focus();
      if (codeArea.select) codeArea.select();
      if (codeArea.setSelectionRange) {
        try { codeArea.setSelectionRange(0, codeArea.value.length); } catch (e) {}
      }
      copyStatus.textContent = '已全选文本框，可长按 / 复制';
    }
    function copyCode() {
      var code = codeArea.value || generate(true);
      var done = function (m) { copyStatus.textContent = m; };
      var fallback = function () {
        try {
          codeArea.focus();
          if (codeArea.select) codeArea.select();
          var ok = document.execCommand && document.execCommand('copy');
          done(ok ? '已复制（兼容模式）' : '复制不可用：已全选文本框，请手动长按 / 复制');
        } catch (e) { done('复制不可用：已全选文本框，请手动复制'); }
      };
      if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
        try {
          var p = navigator.clipboard.writeText(code);
          if (p && p.then) p.then(function () { done('已复制到剪贴板'); }, fallback);
          else fallback();
        } catch (e) { fallback(); }
      } else fallback();
    }
    function shareCode() {
      var code = codeArea.value || generate(true);
      if (typeof navigator !== 'undefined' && navigator.share) {
        try {
          var p = navigator.share({
            title: 'Nihongo 80 回传码 · 第 ' + day.day + ' 天',
            text: code
          });
          if (p && p.catch) p.catch(function () {});
        } catch (e) { copyStatus.textContent = '系统分享未成功，请用「复制回传码」'; }
      } else {
        copyStatus.textContent = '此浏览器不支持系统分享，请用「复制回传码」或「下载 .txt」';
      }
    }
    function downloadCode() {
      var code = codeArea.value || generate(true);
      try {
        var blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'nh80-day-' + pad3(day.day) + '-' + state.session + '.txt';
        document.body.appendChild(a);
        if (a.click) a.click();
        document.body.removeChild(a);
        if (URL.revokeObjectURL && typeof setTimeout !== 'undefined') {
          setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
        }
        copyStatus.textContent = '已下载 .txt 备份，稍后可从中复制导入';
      } catch (e) {
        copyStatus.textContent = '下载不可用，请「复制回传码」或「全选文本」';
      }
    }
    function finish() {
      generate(true);
      if (returnBox.scrollIntoView) {
        try { returnBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch (e) {}
      }
    }

    copyBtn.addEventListener('click', copyCode);
    selectBtn.addEventListener('click', selectCode);
    shareBtn.addEventListener('click', shareCode);
    dlBtn.addEventListener('click', downloadCode);
    regenBtn.addEventListener('click', function () { generate(true); copyStatus.textContent = '已重新生成'; });
    tbFinish.addEventListener('click', finish);
    tbCopy.addEventListener('click', copyCode);

    function showReveal(q, r, box, onChange) {
      box.innerHTML = '';
      if (r && r.revealed_before_submit) box.appendChild(revealNoticeNode());
      var badge = el('span', 'badge badge-good', '答对');
      if (r && r._graded) {
        badge = r.correct
          ? el('span', 'badge badge-good', '答对')
          : el('span', 'badge badge-bad', '未答对 / 待复核');
        box.appendChild(badge);
      }
      box.appendChild(el('div', 'reveal-row', '你的答案：' + (r && r.answer ? r.answer : '（空）')));
      if (q.answer) box.appendChild(el('div', 'reveal-row', '参考答案：' + q.answer));
      if (q.rationale) box.appendChild(el('div', 'reveal-row', '解析：' + q.rationale));
      if (q.rubric) {
        var rub = el('div', 'rubric');
        rub.appendChild(el('div', 'rubric-title', '评分准则（自评）'));
        String(q.rubric).split(/\n+/).forEach(function (t) {
          if (t.trim()) rub.appendChild(el('div', 'rubric-item', t.trim()));
        });
        box.appendChild(rub);
      }
      if (q.type === 'free_production' || q.type === 'dialogue' || !q.answer) {
        var sa = el('div', 'self-assess');
        sa.appendChild(el('span', '', '自评：'));
        var yes = el('button', 'btn btn-mini', '达成');
        var no = el('button', 'btn btn-mini', '未达成');
        yes.type = no.type = 'button';
        yes.addEventListener('click', function () {
          r.correct = true; save();
          badge.className = 'badge badge-good'; badge.textContent = '答对（自评达成）';
          if (onChange) onChange();
        });
        no.addEventListener('click', function () {
          r.correct = false; save();
          badge.className = 'badge badge-bad'; badge.textContent = '未达成（自评）';
          if (onChange) onChange();
        });
        sa.appendChild(yes); sa.appendChild(no);
        box.appendChild(sa);
      }
      if (!r.correct) {
        var et = el('div', 'err-type');
        et.appendChild(el('span', '', '错误类型（可选）：'));
        var sel = el('select', 'sel');
        [['', '（不指定）'], ['forgetting', '遗忘'], ['meaning_confusion', '词义混淆'],
         ['particle', '助词'], ['conjugation', '变形'], ['listening', '听力'],
         ['comprehension', '理解'], ['kanji_reading', '汉字读音'],
         ['orthography', '书写'], ['other', '其他']].forEach(function (o) {
          var op = el('option', '', o[1]);
          op.value = o[0];
          sel.appendChild(op);
        });
        sel.value = r.error_type || '';
        sel.addEventListener('change', function () {
          r.error_type = sel.value || null; save(); if (onChange) onChange();
        });
        et.appendChild(sel);
        box.appendChild(et);
      }
    }

    var cards = [];
    function makeCard(q, i) {
      state.started[q.id] = Date.now();
      var node = el('details', 'q-card');
      node.setAttribute('data-qid', q.id);
      if (mode === 'step') node.open = true;   // 手机：正文常显，仅 active 卡可见
      var sum = el('summary', 'q-sum');
      if (mode === 'step') {
        sum.addEventListener('click', function (e) { if (e.preventDefault) e.preventDefault(); });
      }
      var head = el('div', 'q-head');
      head.appendChild(el('span', 'q-no', '第 ' + (i + 1) + ' / ' + qs.length + ' 题'));
      head.appendChild(el('span', 'q-type', q.type));
      head.appendChild(el('span', 'q-diff', '难度 ' + (q.difficulty || '-')));
      var status = el('span', 'q-status', '未答');
      head.appendChild(status);
      sum.appendChild(head);
      if (q.prompt_zh) sum.appendChild(el('p', 'q-prompt-zh', q.prompt_zh));
      if (q.prompt_ja) sum.appendChild(el('p', 'q-prompt-ja', q.prompt_ja));
      node.appendChild(sum);

      var body = el('div', 'q-body');
      if (q.audio_text) {
        var arow = el('div', 'q-audio');
        var play = el('button', 'btn btn-mini', '朗读题目');
        play.type = 'button';
        var stop = el('button', 'btn btn-mini', '停止');
        stop.type = 'button';
        var anotice = el('div', 'inline-notice');
        anotice.hidden = true;
        play.addEventListener('click', function () { primeTTS(); speak(q.audio_text, anotice); });
        stop.addEventListener('click', function () { stopSpeak(); });
        arow.appendChild(play); arow.appendChild(stop); arow.appendChild(anotice);
        body.appendChild(arow);
        body.appendChild(el('div', 'kana-line', '文本读音（TTS 降级/对照）：' + q.audio_text));
      }

      var inputWrap = el('div', 'q-input');
      buildInput(q, inputWrap, '');
      var getValue = inputWrap._getValue;
      var setValue = inputWrap._setValue;
      body.appendChild(inputWrap);

      var hintRow = el('div', 'q-hint-row');
      var hintBtn = el('button', 'btn btn-mini', '显示提示');
      hintBtn.type = 'button';
      var hintBox = el('div', 'hint-box');
      hintBox.hidden = true;
      hintBtn.addEventListener('click', function () {
        hintBox.hidden = false; hintBox.textContent = hintText(q);
        markHint(q);
      });
      hintRow.appendChild(hintBtn); hintRow.appendChild(hintBox);
      body.appendChild(hintRow);

      var actionRow = el('div', 'q-actions');
      var showAns = el('button', 'btn', '看答案 / 解析');
      showAns.type = 'button';
      var submit = el('button', 'btn btn-primary q-submit', '提交答案');
      submit.type = 'button';
      actionRow.appendChild(showAns); actionRow.appendChild(submit);
      body.appendChild(actionRow);

      var reveal = el('div', 'reveal');
      body.appendChild(reveal);
      node.appendChild(body);

      function markHint(q2) {
        var r = state.results[q2.id];
        if (!r) {
          r = { qid: q2.id, answer: '', correct: false, hinted: true,
                seconds: elapsed(q2.id), error_type: null };
          state.results[q2.id] = r;
        }
        markRevealed(r, getValue ? getValue() : r.answer, false);
        save();
      }
      function paintStatus(r) {
        status.textContent = r.correct ? '答对' : '未答对';
        status.className = 'q-status ' + (r.correct ? 'ok' : 'bad');
      }
      function doSubmit() {
        var r = state.results[q.id];
        if (r && r._graded) return;
        var ans = getValue();
        if (!r) {
          r = { qid: q.id, answer: ans, correct: false, hinted: false,
                seconds: elapsed(q.id), error_type: null };
        }
        r.answer = ans;
        /* 已揭示 / 已提示后提交，hinted 只能保持 true，不能回退（契约 §3.1）。 */
        r.hinted = !!(r.hinted || r.revealed_before_submit);
        var g = gradeAnswer(q, ans);
        if (g !== null) r.correct = g;
        else if (r.correct === null || r.correct === undefined) r.correct = false;
        r._graded = true;
        state.results[q.id] = r;
        save();
        submit.disabled = true;
        showReveal(q, r, reveal, updateChrome);
        paintStatus(r);
        updateChrome();
      }
      showAns.addEventListener('click', function () {
        var r = state.results[q.id];
        if (!r) {
          r = { qid: q.id, answer: getValue(), correct: false, hinted: true,
                seconds: elapsed(q.id), error_type: null };
          state.results[q.id] = r;
        }
        markRevealed(r, getValue(), true);
        save();
        reveal.hidden = false;
        showReveal(q, r, reveal, updateChrome);
        if (!r._graded) submit.textContent = REVEAL_SUBMIT_LABEL;
      });
      submit.addEventListener('click', doSubmit);

      var existing = state.results[q.id];
      if (existing) {
        if (setValue) setValue(existing.answer);
        submit.disabled = true;
        showReveal(q, existing, reveal, updateChrome);
        paintStatus(existing);
        if (existing.hinted) { hintBox.hidden = false; hintBox.textContent = hintText(q); }
        if (existing.revealed_before_submit) submit.textContent = REVEAL_SUBMIT_LABEL;
      }
      return { node: node, q: q, submit: doSubmit };
    }
    function updateChrome() {
      var done = Object.keys(state.results).length;
      var total = qs.length;
      var sub = mode === 'step'
        ? ('第 ' + (state.index + 1) + ' / ' + total + ' 题')
        : ('第 ' + day.day + ' 天 · 共 ' + total + ' 题');
      setProgress(done, total, '已答 ' + done + ' / ' + total + ' 题', sub);
      tbProgress.textContent = '已答 ' + done + ' / ' + total + ' 题';
      setActDisabled('prev', mode !== 'step' || state.index <= 0);
      setActDisabled('next', mode !== 'step' || state.index >= total - 1);
      var cur = mode === 'step' ? cards[state.index] : null;
      var graded = cur && state.results[cur.q.id] && state.results[cur.q.id]._graded;
      setActDisabled('submit', mode !== 'step' || !!graded);
      setActDisabled('finish', total === 0);
    }
    function setActDisabled(act, disabled) {
      var ab = byId('actionbar');
      if (!ab || !ab.children) return;
      Array.prototype.forEach.call(ab.children, function (b) {
        if (b.getAttribute && b.getAttribute('data-act') === act) b.disabled = !!disabled;
      });
    }
    function setActive(i) {
      if (mode !== 'step' || i < 0 || i >= qs.length) return;
      state.index = i;
      cards.forEach(function (c, idx) {
        if (idx === i) c.node.classList.add('active');
        else c.node.classList.remove('active');
      });
      updateChrome();
      var n = cards[i].node;
      if (n.scrollIntoView) { try { n.scrollIntoView({ block: 'start' }); } catch (e) {} }
    }

    QUIZ = {
      state: state,
      total: qs.length,
      lastCode: '',
      prev: function () { setActive(state.index - 1); },
      next: function () { setActive(state.index + 1); },
      submit: function () { if (mode === 'step' && cards[state.index]) cards[state.index].submit(); },
      finish: finish,
      copy: copyCode
    };

    if (qs.length) {
      var list = el('div', 'q-list ' + (mode === 'grid' ? 'grid-mode' : 'step-mode'));
      qs.forEach(function (q, i) { cards.push(makeCard(q, i)); });
      cards.forEach(function (c) { list.appendChild(c.node); });
      root.appendChild(list);
      if (mode === 'step') setActive(0);
    } else {
      root.appendChild(el('p', 'muted', '本日暂无题目；仍可生成空结果的回传码。'));
    }
    updateChrome();
    return sec;
  }

  /* ================= v3：一课教材的 8 个区块（首屏即可学） ================= */

  /* ① 今天要会的 3 句话：日文大字 + 假名（有才显示，不伪造）+ 中文 + 中文提示 + 听。 */
  function renderLessonCore(day) {
    var core = day.lesson_core || [];
    var box = sectionPlain('今天要会的 3 句话',
      '点「听」听发音，没声音就照着假名跟读。');
    if (!core.length) {
      box.appendChild(el('p', 'muted', '（今天暂时没有可展示的句子，先看下面的单词。）'));
      return box;
    }
    core.forEach(function (s, i) {
      var card = el('div', 'core-sentence');
      var main = el('div', 'core-main');
      main.appendChild(el('div', 'core-ja', t(s.ja)));
      if (t(s.kana)) main.appendChild(el('div', 'core-kana', s.kana));  // 有才显示，不伪造
      main.appendChild(el('div', 'core-zh', t(s.zh)));
      /* lesson_core[].note_zh 由课程层生成、未必与本句对应，故不逐句渲染；
         中文难点统一放到语法区「今日难点」常显，避免错配与首屏拥挤。 */
      var side = el('div', 'core-side');
      side.appendChild(listenBtn(t(s.audio_text) || t(s.ja), '听这句'));
      card.appendChild(main); card.appendChild(side);
      box.appendChild(card);
    });
    return box;
  }

  /* ② 单词：常显、不折叠、不翻面；假名常显；全字段 + 韩语对照 + 易错提示。 */
  function renderVocabBlock(day) {
    var vs = day.vocab || [];
    var box = sectionPlain('单词',
      '每个词都常显：先读假名、听发音，再看中文意思、例句、中文易错点和韩语对照。');
    var list = el('div', 'vlist');
    vs.forEach(function (v) {
      var c = el('div', 'vcard');
      var top = el('div', 'vcard-top');
      top.appendChild(el('span', 'v-surface', t(v.surface)));
      if (t(v.kana)) top.appendChild(el('span', 'v-kana', v.kana));
      top.appendChild(listenBtn(t(v.surface) || t(v.kana), '听这个词'));
      c.appendChild(top);
      var meta = el('div', 'v-meta');
      if (t(v.romaji)) meta.appendChild(el('span', 'v-tag', '罗马字 ' + v.romaji));
      if (t(v.pos)) meta.appendChild(el('span', 'v-tag', '词性 ' + zhPos(v.pos)));
      if (t(v.jlpt)) meta.appendChild(el('span', 'v-tag', 'JLPT ' + v.jlpt));
      if (meta.children.length) c.appendChild(meta);
      if (t(v.meaning_zh)) c.appendChild(el('div', 'v-meaning', '中文：' + v.meaning_zh));
      var exLimit = LAYOUT.wide ? 2 : 1;   // 手机更紧凑：每卡 1 例句，PC 最多 2 例句
      (v.examples || []).slice(0, exLimit).forEach(function (e) {
        var ex = el('div', 'v-ex');
        ex.appendChild(el('div', 'v-ex-ja', t(e.ja)));
        if (t(e.zh)) ex.appendChild(el('div', 'v-ex-zh', e.zh));
        ex.appendChild(listenBtn(t(e.audio_text) || t(e.ja), '听'));
        c.appendChild(ex);
      });
      if (t(v.notes_for_zh)) c.appendChild(el('div', 'note-zh', '中文易错：' + v.notes_for_zh));
      if (t(v.ko) || t(v.ko_hint) || t(v.caution)) {
        var kb = el('div', 'ko-box');
        kb.appendChild(el('div', 'ko-title', '韩语对照（结构可以借，词不能猜）'));
        if (t(v.ko)) kb.appendChild(el('div', 'ko-line', '可以对照：' + v.ko));
        if (t(v.ko_hint)) kb.appendChild(el('div', 'ko-hint', v.ko_hint));
        if (t(v.caution)) kb.appendChild(el('div', 'ko-caution', '必须验证 / 不等价：' + v.caution));
        c.appendChild(kb);
      }
      list.appendChild(c);
    });
    if (!vs.length) box.appendChild(el('p', 'muted', '（今天没有新词）'));
    box.appendChild(list);
    return box;
  }

  /* ③ 语法：中文意思 / 中文接续说明 / 例句 / 使用场景 / 易错点 / 相近语法 / 韩语对照。 */
  function renderGrammarBlock(day) {
    var gs = day.grammar || [];
    var box = sectionPlain('语法',
      '用中文讲清楚：什么意思、怎么接续、怎么用、容易错在哪，再对照韩语。');
    gs.forEach(function (g) {
      var c = el('div', 'gcard');
      c.appendChild(el('div', 'g-pattern', t(g.pattern)));
      if (t(g.meaning_zh)) lineIf(c, '意思', g.meaning_zh);
      if (t(g.explanation_zh)) c.appendChild(el('div', 'g-expl', '中文接续说明：' + g.explanation_zh));
      else if (t(g.connection)) lineIf(c, '接续', g.connection);
      if (t(g.usage)) lineIf(c, '使用场景', g.usage);
      var exs = g.examples || [];
      if (exs.length) {
        var ebox = el('div', 'g-exs');
        ebox.appendChild(el('div', 'sub-title', '例句（点「听」跟读）'));
        exs.slice(0, 3).forEach(function (e) {
          var ex = el('div', 'g-ex');
          ex.appendChild(el('span', 'g-ex-ja', t(e.ja)));
          if (t(e.zh)) ex.appendChild(el('span', 'g-ex-zh', e.zh));
          ex.appendChild(listenBtn(t(e.audio_text) || t(e.ja), '听'));
          ebox.appendChild(ex);
        });
        c.appendChild(ebox);
      }
      var errs = g.common_errors || [];
      if (errs.length) {
        var eb = el('div', 'err-box');
        eb.appendChild(el('div', 'sub-title', '易错点（中文）'));
        errs.forEach(function (e, k) {
          var s2 = (k + 1) + '. ' + t(e.why || '');
          if (t(e.wrong) || t(e.fix)) {
            s2 += '（';
            if (t(e.wrong)) s2 += '常见错例：' + e.wrong;
            if (t(e.fix)) s2 += (t(e.wrong) ? '；正确：' : '正确：') + e.fix;
            s2 += '）';
          }
          eb.appendChild(el('div', 'err-item', s2));
        });
        c.appendChild(eb);
      }
      var cmp = g.compare || [];
      if (cmp.length) {
        var cb = el('div', 'cmp-box');
        cb.appendChild(el('div', 'sub-title', '与相近语法的区别'));
        cmp.forEach(function (x) {
          /* 只给中文区别，不展示内部 G 编号。 */
          cb.appendChild(el('div', 'cmp-item', t(x.diff)));
        });
        c.appendChild(cb);
      }
      if (t(g.ko) || t(g.ko_hint) || t(g.caution)) {
        var kb = el('div', 'ko-box');
        kb.appendChild(el('div', 'ko-title', '韩语对照（结构可以借，词不能猜）'));
        if (t(g.ko)) kb.appendChild(el('div', 'ko-line', '可以对照：' + g.ko));
        if (t(g.ko_hint)) kb.appendChild(el('div', 'ko-hint', g.ko_hint));
        if (t(g.caution)) kb.appendChild(el('div', 'ko-caution', '必须验证 / 不等价：' + g.caution));
        c.appendChild(kb);
      }
      box.appendChild(c);
    });
    if (!gs.length) box.appendChild(el('p', 'muted', '（今天没有新语法）'));
    /* 课程层 teaching_notes（中文难点讲解）在学习区常显，不藏到提交后。 */
    var notes = day.teaching_notes || [];
    if (notes.length) {
      var nb = el('div', 'note-zh');
      nb.appendChild(el('div', 'sub-title', '今日难点（中文讲解）'));
      notes.forEach(function (n) { nb.appendChild(el('div', '', t(n))); });
      box.appendChild(nb);
    }
    return box;
  }

  /* ④ 汉字：音读 / 训读 / 例词 / 中文陷阱，明写不要求抄写。 */
  function renderKanjiBlock(day) {
    var ks = day.kanji || [];
    var box = sectionPlain('汉字', '会认、会读、能在词里读出来即可，不要求机械抄写。');
    var list = el('div', 'klist');
    ks.forEach(function (k) {
      var c = el('div', 'kcard');
      c.appendChild(el('div', 'k-char', t(k.char)));
      if (t(k.meaning_zh)) c.appendChild(el('div', 'k-mean', '意思：' + k.meaning_zh));
      lineIf(c, '音读', (k.onyomi || []).join(' / '));
      lineIf(c, '训读', (k.kunyomi || []).join(' / '));
      var exs = k.examples || [];
      if (exs.length) {
        var eb = el('div', 'k-ex-list');
        eb.appendChild(el('div', 'sub-title', '例词'));
        exs.forEach(function (e) {
          eb.appendChild(el('div', 'k-ex',
            t(e.ja) + (t(e.kana) ? '（' + e.kana + '）' : '') + (t(e.zh) ? ' ' + e.zh : '')));
        });
        c.appendChild(eb);
      }
      if (t(k.zh_trap)) c.appendChild(el('div', 'trap', '中文母语者陷阱：' + k.zh_trap));
      if (t(k.ko_hint)) c.appendChild(el('div', 'ko-hint', k.ko_hint));
      c.appendChild(el('div', 'k-note', '不要求机械抄写：会认、会读、能在词里读出来即可。'));
      c.appendChild(listenBtn(t(k.char), '听'));
      list.appendChild(c);
    });
    if (!ks.length) box.appendChild(el('p', 'muted', '（今天没有新汉字）'));
    box.appendChild(list);
    return box;
  }

  /* ⑤ 例句 / 会话：原文与假名读音两个不同节点；audio_text 只用于 TTS。 */
  function renderExamplesBlock(day) {
    var ms = day.materials || [];
    var box = sectionPlain('例句 / 会话',
      '日文原文与假名读音分开给：原文是「写在纸上的样子」，假名是「怎么念」。点「听」听整段。');
    ms.forEach(function (m) {
      var c = el('div', 'material');
      c.appendChild(el('h3', 'material-title',
        (m.kind === 'listening' ? '听力 · ' : '阅读 · ') + t(m.title)));
      if (t(m.text_ja)) c.appendChild(el('div', 'ja-text', m.text_ja));
      /* 只有确有真实假名、且与原文不同时才显示读音行；绝不把 audio_text 当读音。 */
      if (t(m.text_kana) && m.text_kana !== m.text_ja) {
        c.appendChild(el('div', 'kana-line', '假名读音：' + m.text_kana));
      }
      if (t(m.text_zh)) c.appendChild(el('div', 'm-zh', '中文：' + m.text_zh));
      var row = el('div', 'material-actions');
      row.appendChild(listenBtn(t(m.audio_text) || t(m.text_ja), '听这段'));
      c.appendChild(row);
      if (t(m.focus_zh)) c.appendChild(el('div', 'note-zh', '难点：' + m.focus_zh));
      box.appendChild(c);
    });
    if (!ms.length) box.appendChild(el('p', 'muted', '（今天没有会话素材）'));
    return box;
  }

  /* ⑦ 今日复习：优先真实 FSRS 到期项；没有记忆记录时才展示「预习建议」。
     三条分支见 REVISION_CONTRACT §4；自评必须先显示答案才可点（§3.1）。 */
  var CAP_ZH = {
    meaning: '认意思', reading: '读音', listening: '听解', usage: '用法', production: '产出'
  };
  function renderReviewBlock(day, state) {
    var review = (day.review && typeof day.review === 'object') ? day.review : null;
    var due = (review && review.due) ? review.due : [];
    /* 旧数据没有 review 对象时退回 review_plan（视为预习建议，不宣称到期）。 */
    var planned = (review && review.planned) ? review.planned
      : (review ? [] : (day.review_plan || []));
    var box = sectionPlain('今日复习（记忆曲线）',
      '先遮住中文自己想，再点开对答案，最后选「记住了 / 模糊 / 忘了」。');
    if (!due.length && !planned.length) {
      box.appendChild(el('div', 'review-empty', '今天没有到期项。'));
      var news = (day.vocab || []).map(function (v) { return t(v.surface); }).filter(Boolean);
      if (news.length) box.appendChild(el('div', 'review-new',
        '今天新学：' + news.join(' / ') + '。明天会开始带你回忆这几个词。'));
      box.appendChild(el('div', 'review-why',
        '没有到期项就是没有到期项：本页不编造复习任务，也不把「读完页面」记为复习。'));
      return box;
    }
    var isFsrs = due.length > 0;
    var items = isFsrs ? due : planned;
    if (isFsrs) {
      box.appendChild(el('p', 'review-disclaimer',
        '下面是本地 SQLite 里真实到期的 FSRS 记忆卡；到期时间由 FSRS 计算，页面只记录你的自评，不替你判定掌握。'));
      box.appendChild(el('div', 'review-count', '今天真正到期（FSRS） · 共 ' + due.length + ' 项'));
    } else {
      box.appendChild(el('p', 'review-disclaimer',
        '下面是预习建议（按粗略间隔生成），这些不是 FSRS 到期项；实际到期以本地 SQLite / WorkBuddy 会话为准。'));
      box.appendChild(el('div', 'review-count', '预习建议（尚未建立记忆记录） · 共 ' + planned.length + ' 项'));
    }
    items.forEach(function (p, i) {
      var kid = t(p.kid || p.knowledge_id);
      var rateKid = t(p.card_key) || kid;   /* 能力卡按 kid|capability 精确排期 */
      var it = el('div', 'review-item');
      if (p.planned_only) it.setAttribute('data-planned-only', '1');
      var head = el('div', 'review-head');
      head.appendChild(el('span', 'review-no', String(i + 1)));
      head.appendChild(el('span', 'review-surface', t(p.surface)));
      if (t(p.kana)) head.appendChild(el('span', 'review-kana', p.kana));
      head.appendChild(listenBtn(t(p.surface) || t(p.kana), '听'));
      it.appendChild(head);
      var ansRow = el('div', 'review-ans');
      var showBtn = el('button', 'btn btn-mini', '显示答案');
      showBtn.type = 'button';
      var zhSpan = el('span', 'review-zh', '');
      zhSpan.hidden = true;
      ansRow.appendChild(showBtn); ansRow.appendChild(zhSpan);
      it.appendChild(ansRow);
      if (isFsrs) {
        var over = Number(p.overdue_days || 0);
        var meta = '到期：' + t(p.due);
        if (over > 0) meta += ' · 已逾期 ' + over + ' 天';
        if (t(p.capability)) meta += ' · 能力：' + (CAP_ZH[t(p.capability)] || t(p.capability));
        if (t(p.stage)) meta += ' · 阶段：' + t(p.stage);
        it.appendChild(el('div', 'review-next', meta));
      } else {
        it.appendChild(el('div', 'review-reason', '为什么是今天：' + t(p.reason_zh)));
        if (t(p.next_hint_zh)) it.appendChild(el('div', 'review-next', t(p.next_hint_zh)));
      }
      var rates = el('div', 'rating-btns');
      rates.appendChild(el('span', 'rating-label', '回想一下：'));
      var btns = [];
      [['good', '记住了'], ['hard', '模糊'], ['again', '忘了']].forEach(function (o) {
        var b = el('button', 'btn btn-mini rate-btn', o[1]);
        b.type = 'button';
        b.disabled = true;   /* 未显示答案不得自评 */
        b.addEventListener('click', function () {
          if (b.disabled) return;
          if (state && rateKid) { state.reviewRatings[rateKid] = o[0]; if (QUIZ && QUIZ.save) QUIZ.save(); }
          btns.forEach(function (x) { x.classList.remove('sel'); });
          b.classList.add('sel');
        });
        btns.push(b);
        rates.appendChild(b);
      });
      showBtn.addEventListener('click', function () {
        zhSpan.textContent = t(p.zh); zhSpan.hidden = false; showBtn.hidden = true;
        btns.forEach(function (x) { x.disabled = false; });
      });
      it.appendChild(rates);
      box.appendChild(it);
    });
    return box;
  }

  /* ⑧ 页尾折叠：给老师 / 系统。能力目标、时间块、图表、术语、TTS、回传码全在这里。 */
  function renderTeacherBlock(day, site) {
    var d = el('details', 'teacher');
    d.appendChild(el('summary', 'section-sum', '给老师 / 系统（课程编排与系统信息，点开查看）'));
    var body = el('div', 'section-body');
    d.appendChild(body);
    body.appendChild(el('p', 'teacher-lead',
      '下面是排课、统计与工程信息，不影响今天学日语。学员看上面的 7 个区块就够了。'));

    if (t(day.can_do)) {
      var s1 = section('今天要会做的事', false);
      s1._body.appendChild(el('p', '', day.can_do));
      body.appendChild(s1);
    }
    if ((day.focus || []).length) {
      var fz = { listening: '听', reading: '读', speaking: '说', writing: '写',
                 production: '表达', grammar: '语法' };
      var fparts = day.focus.map(function (f) { return fz[f] || t(f); });
      body.appendChild(el('p', 'muted', '今天重点：' + fparts.join(' / ')));
    }
    if (t(day.assessment) && day.assessment !== 'none') {
      body.appendChild(el('p', 'muted', '评估标签：' + assessmentZh(day.assessment)));
    }
    if (t(day.scene)) body.appendChild(el('p', 'muted', '真实场景：' + day.scene));

    if ((day.objectives || []).length) {
      var so = section('能力目标（教研用语）', false);
      var ul = el('ul', 'objectives');
      day.objectives.forEach(function (o) { ul.appendChild(el('li', '', o)); });
      so._body.appendChild(ul); body.appendChild(so);
    }
    var st = section('60 分钟时间块（排课视角）', false);
    st._body.appendChild(timeBar(day.blocks, day.minutes));
    body.appendChild(st);
    var sv = section('当日可视化（课程结构，不代表掌握进度）', false);
    var vg = el('div', 'viz-grid');
    vg.appendChild(vizCard('当日结构', dayStructureSVG(day)));
    vg.appendChild(vizCard('80 天进度热力图', heatmapSVG(site, day.day), 'viz-heat'));
    vg.appendChild(vizCard('题型分布', typeDistSVG(day.questions)));
    sv._body.appendChild(vg);
    sv._body.appendChild(phaseLegend());
    body.appendChild(sv);

    if ((day.teaching_notes || []).length) {
      var sn = section('中文难点讲解（备课用）', false);
      day.teaching_notes.forEach(function (n) { sn._body.appendChild(el('p', '', n)); });
      body.appendChild(sn);
    }
    body.appendChild(el('p', 'muted',
      '来源编号、内部 ID、评估标签与课程结构数据仅用于教研溯源，不在学习区展示。'));

    /* TTS 设备自检 / 语速控件降级到页尾折叠（保留手势解锁与降级提示）。 */
    var banner = byId('tts-banner');
    if (banner) body.appendChild(banner);
    /* 回传码面板（由 buildPracticeV3 生成）挂到页尾折叠区，移出前 3 屏。 */
    if (QUIZ && QUIZ.returnBox) body.appendChild(QUIZ.returnBox);
    body.appendChild(el('p', 'muted',
      '术语：摸底（不计分，只用来定起点）；复习任务分为「FSRS 到期项」与「预习建议（尚未建立记忆记录）」两种，页面会分别标注；把成绩带回 WorkBuddy（回传码）。网页不向任何服务器发送学习数据，学习状态以本地 SQLite / WorkBuddy 会话为准。'));
    return d;
  }

  /* ⑥ 练习：默认展开、由易到难；先想 → 看答案 → 解析+示范句+rubric；逐题中文化反馈。
     保留逐题判分 / 复制·分享·下载回传码 / 手势解锁等既有机制；
     复习自评与开放题自评都写独立字段，绝不写进 results[].correct。 */
  function buildPracticeV3(day) {
    var TYPE_ORDER = { listen: 0, mcq: 1, read: 1, fill: 2, reorder: 3,
                       translate: 4, error_correct: 5, dialogue: 6, free_production: 7 };
    var qs = (day.questions || []).slice().sort(function (a, b) {
      var da = a.difficulty || 0, db = b.difficulty || 0;
      if (da !== db) return da - db;
      var ta = TYPE_ORDER[a.type] === undefined ? 9 : TYPE_ORDER[a.type];
      var tb = TYPE_ORDER[b.type] === undefined ? 9 : TYPE_ORDER[b.type];
      return ta - tb;
    });
    var state = { day: day.day, index: 0, session: null, results: {},
                  started: {}, reviewRatings: {} };
    var mode = LAYOUT.mode;

    var sec = sectionPlain('练一练（学完马上做）',
      '先自己想，再点「看答案」对照解析与示范句；也可以直接「提交答案」看判分。开放题没有唯一答案，照着示范句把自己的话写进去也对。');

    if (mode === 'step') {
      var viewRow = el('div', 'btn-row');
      var viewAll = el('button', 'btn btn-mini', '查看全部题目 / 回看解析');
      viewAll.type = 'button';
      viewAll.addEventListener('click', function () {
        var list = sec.querySelector('.q-list');
        if (!list) return;
        var all = list.classList.contains('grid-mode');
        list.classList.toggle('grid-mode', !all);
        list.classList.toggle('step-mode', all);
        viewAll.textContent = all ? '查看全部题目 / 回看解析' : '回到一屏一题';
      });
      viewRow.appendChild(viewAll);
      sec.appendChild(viewRow);
    }

    var root = el('div', 'quiz quiz-' + mode);
    sec.appendChild(root);

    /* 当日恢复：localStorage 只是刷新/断网缓存，不是状态真源（保留既有机制）。 */
    var saved = null;
    try { saved = JSON.parse(localStorage.getItem('nh80:day:' + day.day) || 'null'); } catch (e) { saved = null; }
    if (saved && saved.results) {
      state.results = saved.results;
      state.session = saved.session || null;
      var rb = el('div', 'banner banner-info',
        '已恢复本机当日缓存（仅用于刷新 / 断网恢复，不是学习状态真源，也不代表已完成）。');
      var clr = el('button', 'btn btn-mini', '清除缓存');
      clr.type = 'button';
      clr.addEventListener('click', function () {
        try { localStorage.removeItem('nh80:day:' + day.day); } catch (e) {}
        if (typeof location !== 'undefined' && location.reload) location.reload();
      });
      rb.appendChild(document.createTextNode(' '));
      rb.appendChild(clr);
      root.appendChild(rb);
    }
    if (saved && saved.reviewRatings) state.reviewRatings = saved.reviewRatings;
    if (!state.session) state.session = makeSessionId();

    /* PC 工具条（保留），文案白话化，不用「已答 X / Y」定义学员。 */
    var toolbar = el('div', 'quiz-toolbar');
    var tbProgress = el('span', 'tb-progress', '共 ' + qs.length + ' 题 · 按自己节奏做');
    var tbFinish = el('button', 'btn btn-primary', '把成绩带回 WorkBuddy');
    tbFinish.type = 'button';
    var tbCopy = el('button', 'btn', '复制回传码');
    tbCopy.type = 'button';
    toolbar.appendChild(tbProgress); toolbar.appendChild(tbFinish); toolbar.appendChild(tbCopy);
    root.appendChild(toolbar);

    /* 回传码面板：白话改名，不出现协议号 / 算法缩写；DOM 由 renderDay 挂到页尾折叠区。 */
    var returnBox = el('details', 'return-box');
    returnBox.appendChild(el('summary', 'section-sum', '把成绩带回 WorkBuddy（复制 / 分享 / 下载）'));
    var rbBody = el('div', 'section-body');
    rbBody.appendChild(el('div', 'return-hint',
      '复制后粘贴到 WorkBuddy 对话即可导入；本页不保存成绩、不向任何服务器发送学习数据，仅保存作答记录，不代表已掌握。'));
    var summary = el('div', 'return-summary', '尚未生成');
    rbBody.appendChild(summary);
    var codeArea = el('textarea', 'code-area');
    codeArea.readOnly = true; codeArea.rows = 4;
    codeArea.setAttribute('aria-label', '回传码文本框（可全选复制）');
    rbBody.appendChild(codeArea);
    var btnRow = el('div', 'btn-row');
    var copyBtn = el('button', 'btn btn-primary', '复制回传码'); copyBtn.type = 'button';
    var selectBtn = el('button', 'btn', '全选文本'); selectBtn.type = 'button';
    var shareBtn = el('button', 'btn', '系统分享'); shareBtn.type = 'button';
    var dlBtn = el('button', 'btn', '下载 .txt'); dlBtn.type = 'button';
    var regenBtn = el('button', 'btn', '重新生成'); regenBtn.type = 'button';
    [copyBtn, selectBtn, shareBtn, dlBtn, regenBtn].forEach(function (b) { btnRow.appendChild(b); });
    rbBody.appendChild(btnRow);
    var copyStatus = el('div', 'copy-status', '');
    rbBody.appendChild(copyStatus);
    returnBox.appendChild(rbBody);
    /* 故意不 append 到 root：由 renderTeacherBlock 挂到页尾折叠区，移出前 3 屏。 */

    var lastCode = '';

    function save() {
      try {
        localStorage.setItem('nh80:day:' + day.day,
          JSON.stringify({ session: state.session, results: state.results,
                           reviewRatings: state.reviewRatings }));
      } catch (e) {}
    }
    function elapsed(qid) {
      if (!state.started[qid]) state.started[qid] = Date.now();
      return Math.round((Date.now() - state.started[qid]) / 1000);
    }
    function generate(open) {
      var payload = makePayload(state);
      autoSync(payload);
      lastCode = encodeReturnCode(payload);
      QUIZ.lastCode = lastCode;
      codeArea.value = lastCode;
      summary.textContent = '共 ' + qs.length + ' 题 · 已记录 ' + payload.results.length
        + ' 条作答 · 复习自评 ' + payload.review_ratings.length + ' 条 · 会话 ' + payload.session;
      if (open) {
        if (TEACHER_BOX) TEACHER_BOX.open = true;
        returnBox.open = true;
      }
      return lastCode;
    }
    function selectCode() {
      codeArea.focus();
      if (codeArea.select) codeArea.select();
      if (codeArea.setSelectionRange) {
        try { codeArea.setSelectionRange(0, codeArea.value.length); } catch (e) {}
      }
      copyStatus.textContent = '已全选文本框，可长按 / 复制';
    }
    function copyCode() {
      var code = codeArea.value || generate(true);
      var done = function (m) { copyStatus.textContent = m; };
      var fallback = function () {
        try {
          codeArea.focus();
          if (codeArea.select) codeArea.select();
          var ok = document.execCommand && document.execCommand('copy');
          done(ok ? '已复制（兼容模式）' : '复制不可用：已全选文本框，请手动长按 / 复制');
        } catch (e) { done('复制不可用：已全选文本框，请手动复制'); }
      };
      if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
        try {
          var p = navigator.clipboard.writeText(code);
          if (p && p.then) p.then(function () { done('已复制到剪贴板'); }, fallback);
          else fallback();
        } catch (e) { fallback(); }
      } else fallback();
    }
    function shareCode() {
      var code = codeArea.value || generate(true);
      if (typeof navigator !== 'undefined' && navigator.share) {
        try {
          var p = navigator.share({ title: 'Nihongo 80 学习记录 · 第 ' + day.day + ' 天', text: code });
          if (p && p.catch) p.catch(function () {});
        } catch (e) { copyStatus.textContent = '系统分享未成功，请用「复制回传码」'; }
      } else {
        copyStatus.textContent = '此浏览器不支持系统分享，请用「复制回传码」或「下载 .txt」';
      }
    }
    function downloadCode() {
      var code = codeArea.value || generate(true);
      try {
        var blob = new Blob([code], { type: 'text/plain;charset=utf-8' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'nh80-day-' + pad3(day.day) + '-' + state.session + '.txt';
        document.body.appendChild(a);
        if (a.click) a.click();
        document.body.removeChild(a);
        if (URL.revokeObjectURL && typeof setTimeout !== 'undefined') {
          setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
        }
        copyStatus.textContent = '已下载 .txt 备份，稍后可从中复制导入';
      } catch (e) {
        copyStatus.textContent = '下载不可用，请「复制回传码」或「全选文本」';
      }
    }
    function finish() {
      generate(true);
      if (returnBox.scrollIntoView) {
        try { returnBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch (e) {}
      }
    }
    copyBtn.addEventListener('click', copyCode);
    selectBtn.addEventListener('click', selectCode);
    shareBtn.addEventListener('click', shareCode);
    dlBtn.addEventListener('click', downloadCode);
    regenBtn.addEventListener('click', function () { generate(true); copyStatus.textContent = '已重新生成'; });
    tbFinish.addEventListener('click', finish);
    tbCopy.addEventListener('click', copyCode);

    /* 解析区预渲染（DOM 里已有文本，初始隐藏）。中文化反馈，不出现英文错误归因枚举。 */
    function renderRevealContent(q, box, r) {
      box.innerHTML = '';
      if (r && r.revealed_before_submit) box.appendChild(revealNoticeNode());
      if (r) {
        if (r._graded) {
          var badge = r.correct
            ? el('span', 'badge badge-good', '答对')
            : el('span', 'badge badge-bad', '再核对一下');
          box.appendChild(badge);
        }
        box.appendChild(el('div', 'reveal-row', '你的答案：' + (r.answer || '（空）')));
      }
      if (t(q.answer)) box.appendChild(el('div', 'reveal-row', '参考答案：' + q.answer));
      if (t(q.rationale)) box.appendChild(el('div', 'reveal-row', '解析：' + q.rationale));
      if (t(q.expected_production)) {
        var ep = el('div', 'demo-box');
        ep.appendChild(el('div', 'demo-title', '示范句（不是唯一答案）'));
        ep.appendChild(el('div', 'demo-ja', q.expected_production));
        ep.appendChild(listenBtn(q.expected_production, '听示范句'));
        box.appendChild(ep);
      }
      if (t(q.rubric)) {
        var rub = el('div', 'rubric');
        rub.appendChild(el('div', 'rubric-title', '评分准则（分点对照）'));
        String(q.rubric).split(/[；;①②③④⑤⑥\n]+/).forEach(function (s2) {
          if (s2.trim()) rub.appendChild(el('div', 'rubric-item', s2.trim()));
        });
        box.appendChild(rub);
      }
      box.appendChild(el('div', 'feedback-zh',
        '下次遇到这类题：先看清句子里的助词和句末，再对照上面的讲解；写错也没关系，重点是知道为什么。'));
      if (q.type === 'free_production' || q.type === 'dialogue' || !t(q.answer)) {
        var sa = el('div', 'self-assess');
        sa.appendChild(el('span', '', '自查（不计入成绩）：'));
        var yes = el('button', 'btn btn-mini', '会了');
        var no = el('button', 'btn btn-mini', '还不熟');
        yes.type = no.type = 'button';
        function setSA(v, label) {
          var cur = state.results[q.id];
          if (cur) { cur.self_assessed = v; save(); }
          var note = sa.querySelector('.self-assess-note');
          if (note) note.textContent = label;
          else sa.appendChild(el('span', 'self-assess-note', label));
          yes.disabled = no.disabled = true;
        }
        yes.addEventListener('click', function () { setSA('yes', '已记录：会了（仅自评，不计成绩）'); });
        no.addEventListener('click', function () { setSA('no', '已记录：还不熟（仅自评，不计成绩）'); });
        sa.appendChild(yes); sa.appendChild(no);
        box.appendChild(sa);
      }
    }
    function showReveal(q, r, box, onChange) {
      renderRevealContent(q, box, r);
      box.hidden = false;
      if (onChange) onChange();
    }

    var cards = [];
    function makeCard(q, i) {
      state.started[q.id] = Date.now();
      var node = el('details', 'q-card');
      node.setAttribute('data-qid', q.id);
      node.open = true;                       /* 默认展开，不点折叠即可作答 */
      var sum = el('summary', 'q-sum');
      if (mode === 'step') {
        sum.addEventListener('click', function (e) { if (e.preventDefault) e.preventDefault(); });
      }
      var head = el('div', 'q-head');
      head.appendChild(el('span', 'q-no', '第 ' + (i + 1) + ' / ' + qs.length + ' 题'));
      head.appendChild(el('span', 'q-type', qTypeZh(q.type)));   /* 中文化题型 */
      var status = el('span', 'q-status', '');
      head.appendChild(status);
      sum.appendChild(head);
      if (t(q.prompt_zh)) sum.appendChild(el('p', 'q-prompt-zh', q.prompt_zh));
      if (t(q.prompt_ja)) sum.appendChild(el('p', 'q-prompt-ja', q.prompt_ja));
      node.appendChild(sum);

      var body = el('div', 'q-body');
      if (t(q.audio_text)) {
        var arow = el('div', 'q-audio');
        var play = el('button', 'btn btn-mini', '听题目'); play.type = 'button';
        var stop = el('button', 'btn btn-mini', '停止'); stop.type = 'button';
        var anotice = el('span', 'inline-notice'); anotice.hidden = true;
        play.addEventListener('click', function () { primeTTS(); speak(q.audio_text, anotice); });
        stop.addEventListener('click', function () { stopSpeak(); });
        arow.appendChild(play); arow.appendChild(stop); arow.appendChild(anotice);
        body.appendChild(arow);
        /* audio_text 只用于 TTS，不再当作可见「文本读音」（修掉读音=原文 bug）。 */
      }
      var inputWrap = el('div', 'q-input');
      buildInput(q, inputWrap, '');
      var getValue = inputWrap._getValue;
      var setValue = inputWrap._setValue;
      body.appendChild(inputWrap);

      var hintRow = el('div', 'q-hint-row');
      var hintBtn = el('button', 'btn btn-mini', '显示提示');
      hintBtn.type = 'button';
      var hintBox = el('div', 'hint-box');
      hintBox.hidden = true;
      hintBtn.addEventListener('click', function () {
        hintBox.hidden = false; hintBox.textContent = hintText(q);
        var r = state.results[q.id];
        if (!r) {
          r = { qid: q.id, answer: getValue(), correct: false, hinted: true,
                seconds: elapsed(q.id), error_type: null };
          state.results[q.id] = r;
        }
        markRevealed(r, getValue(), false);
        save();
      });
      hintRow.appendChild(hintBtn); hintRow.appendChild(hintBox);
      body.appendChild(hintRow);

      var actionRow = el('div', 'q-actions');
      var showAns = el('button', 'btn', '看答案 / 解析'); showAns.type = 'button';
      var submit = el('button', 'btn btn-primary q-submit', '提交答案'); submit.type = 'button';
      actionRow.appendChild(showAns); actionRow.appendChild(submit);
      body.appendChild(actionRow);

      var reveal = el('div', 'reveal');
      reveal.hidden = true;
      renderRevealContent(q, reveal, null);   /* 预渲染：解析/示范句/rubric 已在 DOM 里 */
      body.appendChild(reveal);
      node.appendChild(body);

      function paintStatus(r) {
        status.textContent = r && r.correct ? '答对' : (r ? '再看看' : '');
        status.className = 'q-status ' + (r && r.correct ? 'ok' : (r ? 'bad' : ''));
      }
      function doSubmit() {
        var r = state.results[q.id];
        if (r && r._graded) return;
        var ans = getValue();
        if (!r) {
          r = { qid: q.id, answer: ans, correct: false, hinted: false,
                seconds: elapsed(q.id), error_type: null };
        }
        r.answer = ans;
        /* 已揭示 / 已提示后提交，hinted 只能保持 true，不能回退（契约 §3.1）。 */
        r.hinted = !!(r.hinted || r.revealed_before_submit);
        var g = gradeAnswer(q, ans);
        if (g !== null) r.correct = g;
        else if (r.correct === null || r.correct === undefined) r.correct = false;
        r._graded = true;
        state.results[q.id] = r;
        save();
        submit.disabled = true;
        reveal.hidden = false;
        showReveal(q, r, reveal, updateChrome);
        paintStatus(r);
        updateChrome();
      }
      showAns.addEventListener('click', function () {
        var r = state.results[q.id];
        if (!r) {
          r = { qid: q.id, answer: getValue(), correct: false, hinted: true,
                seconds: elapsed(q.id), error_type: null };
          state.results[q.id] = r;
        }
        markRevealed(r, getValue(), true);
        save();
        reveal.hidden = false;
        showReveal(q, r, reveal, updateChrome);
        if (!r._graded) submit.textContent = REVEAL_SUBMIT_LABEL;
      });
      submit.addEventListener('click', doSubmit);

      var existing = state.results[q.id];
      if (existing) {
        if (setValue) setValue(existing.answer);
        submit.disabled = true;
        reveal.hidden = false;
        showReveal(q, existing, reveal, updateChrome);
        paintStatus(existing);
        if (existing.hinted) { hintBox.hidden = false; hintBox.textContent = hintText(q); }
        if (existing.revealed_before_submit) submit.textContent = REVEAL_SUBMIT_LABEL;
      }
      return { node: node, q: q, submit: doSubmit };
    }
    function updateChrome() {
      var done = Object.keys(state.results).length;
      var total = qs.length;
      var sub = mode === 'step'
        ? ('第 ' + (state.index + 1) + ' / ' + total + ' 题')
        : ('第 ' + day.day + ' 天 · 共 ' + total + ' 题');
      setProgress(done, total, '今天 ' + total + ' 道题 · 先学后练', sub);
      tbProgress.textContent = '共 ' + total + ' 题 · 按自己节奏做';
      setActDisabled('prev', mode !== 'step' || state.index <= 0);
      setActDisabled('next', mode !== 'step' || state.index >= total - 1);
      var cur = mode === 'step' ? cards[state.index] : null;
      var graded = cur && state.results[cur.q.id] && state.results[cur.q.id]._graded;
      setActDisabled('submit', mode !== 'step' || !!graded);
      setActDisabled('finish', total === 0);
    }
    function setActDisabled(act, disabled) {
      var ab = byId('actionbar');
      if (!ab || !ab.children) return;
      Array.prototype.forEach.call(ab.children, function (b) {
        if (b.getAttribute && b.getAttribute('data-act') === act) b.disabled = !!disabled;
      });
    }
    function setActive(i) {
      if (mode !== 'step' || i < 0 || i >= qs.length) return;
      state.index = i;
      cards.forEach(function (c, idx) {
        if (idx === i) c.node.classList.add('active');
        else c.node.classList.remove('active');
      });
      updateChrome();
      var n = cards[i].node;
      if (n.scrollIntoView) { try { n.scrollIntoView({ block: 'start' }); } catch (e) {} }
    }

    QUIZ = {
      state: state,
      total: qs.length,
      lastCode: '',
      returnBox: returnBox,
      save: save,
      prev: function () { setActive(state.index - 1); },
      next: function () { setActive(state.index + 1); },
      submit: function () { if (mode === 'step' && cards[state.index]) cards[state.index].submit(); },
      finish: finish,
      copy: copyCode
    };

    if (qs.length) {
      var list = el('div', 'q-list ' + (mode === 'grid' ? 'grid-mode' : 'step-mode'));
      qs.forEach(function (q, i) { cards.push(makeCard(q, i)); });
      cards.forEach(function (c) { list.appendChild(c.node); });
      root.appendChild(list);
      if (mode === 'step') setActive(0);
    } else {
      root.appendChild(el('p', 'muted', '本日暂无题目。'));
    }
    updateChrome();
    return sec;
  }

  /* ---------------- 页面入口 ---------------- */
  function renderIndex(site) {
    var app = byId('app');
    app.appendChild(el('h1', 'page-title', 'Nihongo 80 · 每日学习'));
    app.appendChild(el('p', 'lead',
      '80 天日语学习计划，同时适配 PC 与手机。每天一页：主题 / 真实场景 / 能力目标 / 60 分钟时间块、词汇·语法·汉字卡、阅读听力素材、分步练习与即时判分，最后生成回传码。'));
    app.appendChild(el('div', 'notice',
      '重要：本网站不是学习状态的真源。状态只存在于本地 SQLite（data/state.db）。网页仅做展示、练习、即时判分并生成「把成绩带回 WorkBuddy」的回传码；不会向任何服务器发送学习数据，也不会把「读完页面」记为完成。'));
    app.appendChild(el('div', 'notice',
      '手机学习闭环：打开当天页面 → 首次点「试听 / 解锁语音」→ 分步练习（一屏一题）→ 完成生成回传码 → 复制 / 系统分享 / 下载 .txt → 回到 WorkBuddy 会话粘贴导入，或先存备忘录稍后导入。离线仅展示，成绩靠回传码。'));

    var sec = section('80 天进度热力图（课程结构）', true);
    sec._body.appendChild(el('p', 'muted',
      '按天展示课程结构：颜色代表阶段（P1–P6），深浅代表当天题量；当前天有描边。窄屏可横向滚动，PC 保持紧凑。数据来自内嵌 JSON，仅是课程计划，不代表你的掌握进度。'));
    sec._body.appendChild(vizCard('课程结构热力图', heatmapSVG(site, null), 'viz-heat'));
    sec._body.appendChild(phaseLegend());
    app.appendChild(sec);

    var list = section('每日入口', true);
    var grid = el('div', 'day-grid');
    var total = (site.meta && site.meta.days) ? site.meta.days : site.days.length;
    var map = {};
    site.days.forEach(function (x) { map[x.day] = x; });
    for (var i = 1; i <= total; i++) {
      var info = map[i];
      var a = el('a', 'day-tile', '');
      a.href = 'day-' + pad3(i) + '.html';
      a.appendChild(el('span', 'day-tile-n', 'D' + pad3(i)));
      if (info) {
        a.appendChild(el('span', 'day-tile-t', info.theme || ''));
        a.appendChild(el('span', 'day-tile-p', info.phase || ''));
      } else {
        a.appendChild(el('span', 'day-tile-t', '（待生成）'));
        a.classList.add('empty');
      }
      grid.appendChild(a);
    }
    list._body.appendChild(grid);
    app.appendChild(list);
  }
  function renderDay(day, site) {
    var app = byId('app');
    /* 标题区：去掉阶段 / ID / 评估 / 英文标签，只留白话目标与主题。 */
    var head = el('div', 'day-head');
    head.appendChild(el('div', 'day-kicker', '第 ' + day.day + ' 天'));
    head.appendChild(el('h1', 'page-title', t(day.theme) || '当日学习'));
    if (t(day.can_do)) head.appendChild(el('p', 'lead', '今天要会做的事：' + day.can_do));
    app.appendChild(head);

    /* 8 区块顺序（REDESIGN_PLAN §3）：首屏即 3 句话 + 常显词卡，不点任何折叠即可学。 */
    app.appendChild(renderLessonCore(day));                              /* ① */
    app.appendChild(renderVocabBlock(day));                             /* ② */
    app.appendChild(renderGrammarBlock(day));                           /* ③ */
    app.appendChild(renderKanjiBlock(day));                             /* ④ */
    app.appendChild(renderExamplesBlock(day));                          /* ⑤ */
    app.appendChild(buildPracticeV3(day));                              /* ⑥（建 QUIZ / returnBox） */
    app.appendChild(renderReviewBlock(day, QUIZ ? QUIZ.state : null));  /* ⑦ */
    /* 收尾可见入口：手机也能一键生成 / 复制回传码（点开页尾折叠区）。 */
    var reWrap = el('div', 'block return-entry');
    reWrap.appendChild(el('h2', 'block-title', '把成绩带回 WorkBuddy'));
    reWrap.appendChild(el('p', 'block-hint',
      '本页不保存成绩、不向任何服务器发送学习数据；点下面生成回传码，复制后粘贴到 WorkBuddy 对话即可。仅保存作答记录，不代表已掌握。'));
    var reBtn = el('button', 'btn btn-primary', '生成 / 查看回传码');
    reBtn.type = 'button';
    reBtn.addEventListener('click', function () { if (QUIZ) QUIZ.finish(); });
    reWrap.appendChild(reBtn);
    app.appendChild(reWrap);
    TEACHER_BOX = renderTeacherBlock(day, site);                        /* ⑧ */
    app.appendChild(TEACHER_BOX);
  }
  function init() {
    detectLayout();
    setupTTSBanner();
    setupChrome();
    var site = readJSON('nh80-site') || { days: [], meta: {} };
    var day = readJSON('nh80-day');
    renderNav(site, day);
    if (day) renderDay(day, site);
    else renderIndex(site);
  }

  /* ---------------- 入口（置于最末，避免 readyState 非 loading 时顶层 var 未初始化） ---------------- */
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
