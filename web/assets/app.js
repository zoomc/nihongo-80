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
  function readJSON(id) {
    var n = byId(id);
    if (!n) return null;
    try { return JSON.parse(n.textContent); } catch (e) { return null; }
  }
  function pad2(n) { return String(n).padStart(2, '0'); }
  function pad3(n) { return String(n).padStart(3, '0'); }
  function norm(s) {
    return String(s === undefined || s === null ? '' : s)
      .replace(/[\s\u3000]+/g, '').toLowerCase();
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
      return {
        qid: r.qid, answer: r.answer, correct: !!r.correct, hinted: !!r.hinted,
        seconds: Math.max(0, Math.round(r.seconds || 0)), error_type: r.error_type || null
      };
    });
    var total = results.reduce(function (a, r) { return a + r.seconds; }, 0);
    return {
      v: 1, day: state.day, session: state.session, ts: localISO(),
      results: results, minutes: Math.max(1, Math.round(total / 60)), source: 'web'
    };
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
      side.textContent = '语音：' + (TTS.supported
        ? (TTS.jaVoice ? 'ja-JP 可用（需手势解锁）' : '无日语语音，降级为假名读音')
        : '不支持，降级为文本 + 假名');
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
        ? '在线 · 课程与素材已缓存，可离线打开；离线仅展示，成绩靠回传码。'
        : '当前离线 · 仅展示已缓存课程；成绩靠回传码回 WorkBuddy 会话导入。';
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
      var badge = r.correct
        ? el('span', 'badge badge-good', '答对')
        : el('span', 'badge badge-bad', '未答对 / 待复核');
      box.appendChild(badge);
      box.appendChild(el('div', 'reveal-row', '你的答案：' + (r.answer || '（空）')));
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
      var submit = el('button', 'btn btn-primary q-submit', '提交答案');
      submit.type = 'button';
      actionRow.appendChild(submit);
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
        r.hinted = true;
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
      submit.addEventListener('click', doSubmit);

      var existing = state.results[q.id];
      if (existing) {
        if (setValue) setValue(existing.answer);
        submit.disabled = true;
        showReveal(q, existing, reveal, updateChrome);
        paintStatus(existing);
        if (existing.hinted) { hintBox.hidden = false; hintBox.textContent = hintText(q); }
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

  /* ---------------- 页面入口 ---------------- */
  function renderIndex(site) {
    var app = byId('app');
    app.appendChild(el('h1', 'page-title', 'Nihongo 80 · 每日学习'));
    app.appendChild(el('p', 'lead',
      '80 天日语学习计划，同时适配 PC 与手机。每天一页：主题 / 真实场景 / 能力目标 / 60 分钟时间块、词汇·语法·汉字卡、阅读听力素材、分步练习与即时判分，最后生成回传码。'));
    app.appendChild(el('div', 'notice',
      '重要：本网站不是学习状态的真源。状态只存在于本地 SQLite（data/state.db）。网页仅做展示、练习、即时判分并生成 NH80R1 回传码；不会向任何服务器发送学习数据，也不会把「读完页面」记为完成。'));
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
    var W = LAYOUT.wide;
    var head = el('div', 'day-head');
    head.appendChild(el('div', 'day-kicker', '第 ' + day.day + ' 天 · ' + (day.phase || '')));
    head.appendChild(el('h1', 'page-title', day.theme || '当日学习'));
    if (day.scene) head.appendChild(el('p', 'scene', '真实场景：' + day.scene));
    if (day.can_do) {
      head.appendChild(el('div', 'banner banner-info cando-card', '本日 Can-do：' + day.can_do));
      if (day.focus && day.focus.length) {
        head.appendChild(el('p', 'muted', '能力侧重：' + day.focus.join(' / ')));
      }
    }
    if (day.assessment && day.assessment !== 'none') {
      head.appendChild(el('span', 'badge', '测评：' + day.assessment));
    }
    app.appendChild(head);

    /* 手机：除练习外默认折叠，避免几十屏滚动；PC 展开更多分区 */
    if (day.objectives && day.objectives.length) {
      var os = section('能力目标', W);
      var ul = el('ul', 'objectives');
      day.objectives.forEach(function (o) { ul.appendChild(el('li', '', o)); });
      os._body.appendChild(ul); app.appendChild(os);
    }

    var ts = section('60 分钟时间块', W);
    ts._body.appendChild(timeBar(day.blocks, day.minutes));
    app.appendChild(ts);

    var vs = section('当日可视化', W);
    var vg = el('div', 'viz-grid');
    vg.appendChild(vizCard('当日结构', dayStructureSVG(day)));
    vg.appendChild(vizCard('80 天进度热力图', heatmapSVG(site, day.day), 'viz-heat'));
    vg.appendChild(vizCard('题型分布', typeDistSVG(day.questions)));
    vs._body.appendChild(vg);
    vs._body.appendChild(phaseLegend());
    app.appendChild(vs);

    if (day.vocab && day.vocab.length) {
      var vsec = section('词汇卡（先自测，再点开看读音与释义）', false);
      vsec._body.appendChild(el('p', 'muted',
        LAYOUT.wide ? '点击卡片翻面查看读音与释义。' : '点击卡片翻面；手机上一次只展开一张，先自测再揭示。'));
      vsec._body.appendChild(cardGrid(day.vocab, vocabCard, !LAYOUT.wide));
      app.appendChild(vsec);
    }
    if (day.grammar && day.grammar.length) {
      var gsec = section('语法卡', false);
      gsec._body.appendChild(cardGrid(day.grammar, grammarCard, false));
      app.appendChild(gsec);
    }
    if (day.kanji && day.kanji.length) {
      var ksec = section('汉字卡（中日差异提示）', false);
      ksec._body.appendChild(cardGrid(day.kanji, kanjiCard, false));
      app.appendChild(ksec);
    }
    if (day.materials && day.materials.length) {
      var msec = section('阅读 / 听力素材', false);
      day.materials.forEach(function (m) { msec._body.appendChild(materialCard(m)); });
      app.appendChild(msec);
    }
    app.appendChild(buildPractice(day));
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
