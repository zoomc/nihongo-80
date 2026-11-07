#!/usr/bin/env python3
"""build_v5_site.py — 生成 v5 每日页（5 块、遮盖背诵、响应式）。

输出：
  web/day-001.html ... day-150.html
  web/data/day-001.json ...
  web/assets/app.css, app.js
  web/index.html
  web/sw.js, manifest.webmanifest
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "knowledge/seeds"
OUT = ROOT / "web"
DATA = OUT / "data"


def read(name):
    return [json.loads(x) for x in (SEED / name).read_text(encoding="utf-8").splitlines() if x.strip()]


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


CSS = r"""
:root{--bg:#fbfaf7;--surface:#fff;--ink:#1d1c1a;--muted:#6b6862;--line:#e4e0d8;
--accent:#b4472e;--ok:#2e7d4f;--bad:#b3261e;--radius:14px;--max:760px}
@media (prefers-color-scheme:dark){:root{--bg:#171614;--surface:#201f1c;--ink:#efede7;
--muted:#a39e94;--line:#35322c;--accent:#e0704f;--ok:#6fbf8f;--bad:#f08a80}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.7 -apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP","PingFang SC",sans-serif}
a{color:var(--accent)}
.wrap{max-width:var(--max);margin:0 auto;padding:14px 14px 96px}
header.top{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--line);
display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 14px}
.top .day{font-weight:700;font-size:18px}
.top .goal{color:var(--muted);font-size:13px;flex:1;min-width:160px}
.top .prog{font-variant-numeric:tabular-nums;color:var(--accent);font-weight:700;font-size:13px}
.mode{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;
padding:6px 12px;font-size:13px;cursor:pointer}
section.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
padding:16px;margin:14px 0}
h2{font-size:16px;margin:0 0 4px;display:flex;align-items:center;gap:8px}
h2 .min{font-size:12px;color:var(--muted);font-weight:400}
.hint{color:var(--muted);font-size:13px;margin:0 0 12px}
.btn{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:10px;
padding:9px 14px;font-size:15px;cursor:pointer}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn:disabled{opacity:.4;cursor:not-allowed}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.vcard{border:1px solid var(--line);border-radius:12px;padding:16px;margin:10px 0}
.surface{font-size:32px;font-weight:700;letter-spacing:.02em;overflow-wrap:anywhere}
.kana{color:var(--muted);font-size:18px}
.meaning{font-size:20px;margin-top:6px}
.ko{color:var(--accent);font-size:14px}
.ex{font-size:15px;margin-top:6px}
.ex .zh{color:var(--muted);font-size:14px}
.mask{filter:blur(6px);color:transparent;user-select:none;transition:filter .12s}
.mask.peek{filter:none;color:inherit}
.eye{border:0;background:none;color:var(--muted);cursor:pointer;font-size:14px;padding:4px}
.gcard{border-top:1px dashed var(--line);padding:12px 0}
.pattern{font-size:22px;font-weight:700}
.conn{color:var(--muted);font-size:14px}
.ko-box{background:var(--bg);border-left:3px solid var(--accent);padding:8px 10px;margin:8px 0;font-size:14px}
textarea{width:100%;min-height:64px;border:1px solid var(--line);border-radius:8px;
background:var(--bg);color:var(--ink);padding:8px;font:inherit}
.q{border-top:1px dashed var(--line);padding:12px 0}
.q .opts{display:grid;gap:6px;margin-top:6px}
.opt{display:flex;gap:8px;align-items:flex-start;border:1px solid var(--line);border-radius:8px;padding:8px;cursor:pointer}
.opt.correct{border-color:var(--ok)} .opt.wrong{border-color:var(--bad)}
.fb{font-size:14px;margin-top:6px} .fb.ok{color:var(--ok)} .fb.bad{color:var(--bad)}
.foot{position:fixed;left:0;right:0;bottom:0;background:var(--surface);border-top:1px solid var(--line);
padding:10px 14px;display:flex;gap:8px;justify-content:center;z-index:30}
.foot .btn{flex:1;max-width:260px}
details summary{cursor:pointer;color:var(--muted);font-size:14px}
.small{font-size:13px;color:var(--muted)}
.done{opacity:.55}
.kstrip{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px;padding-top:10px;border-top:1px dashed var(--line)}
.kchip{font-size:14px;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:4px 8px}
@media(min-width:1024px){
 .wrap{max-width:1120px;display:grid;grid-template-columns:200px minmax(0,760px);gap:24px;align-items:start}
 nav.toc{position:sticky;top:64px;font-size:14px}
 nav.toc a{display:block;padding:6px 0;color:var(--muted);text-decoration:none}
 main{grid-column:2}
 .foot{position:static;background:none;border:0;justify-content:flex-start;margin-top:8px}
}
@media print{
 .foot,header.top,.eye,.btn{display:none!important}
 .mask{filter:none!important;color:inherit!important}
 body{background:#fff;color:#000}
 .wrap{display:block;max-width:none}
}
"""

JS = r"""
(function(){
'use strict';
var STORE='nh80.v5.';
var mode=localStorage.getItem(STORE+'mode')||'zh';  // all|zh|ja|both
function $(s,r){return (r||document).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))}
function applyMode(root){
  $$('[data-role]',root).forEach(function(el){
    var role=el.getAttribute('data-role');
    var hide=(mode==='both')||(mode==='zh'&&role==='zh')||(mode==='ja'&&role==='ja');
    el.classList.toggle('mask',hide);
    el.classList.toggle('peek',!hide&&el.classList.contains('peek'));
    if(!hide) el.classList.remove('mask');
  });
  var b=$('#modeBtn'); if(b) b.textContent={all:'遮盖：关',zh:'遮盖：中文',ja:'遮盖：日语',both:'遮盖：双向'}[mode];
}
function setMode(m){mode=m;localStorage.setItem(STORE+'mode',m);applyMode(document)}
function initMask(){
  $$('.eye').forEach(function(b){
    b.addEventListener('click',function(){
      var card=b.closest('.vcard,.gcard,.ex');
      var order=['all','zh','ja','both'];
      var cur=card.getAttribute('data-mode')||mode;
      var next=order[(order.indexOf(cur)+1)%4];
      card.setAttribute('data-mode',next);
      $$('.mask,[data-role]',card).forEach(function(el){
        if(!el.hasAttribute('data-role'))return;
        var role=el.getAttribute('data-role');
        var hide=(next==='both')||(next==='zh'&&role==='zh')||(next==='ja'&&role==='ja');
        el.classList.toggle('mask',hide); if(!hide)el.classList.remove('peek');
      });
    });
  });
  $$('.mask,[data-role]').forEach(function(el){
    el.addEventListener('click',function(){
      if(!el.classList.contains('mask'))return;
      el.classList.add('peek');
      setTimeout(function(){el.classList.remove('peek')},3000);
    });
  });
  var mb=$('#modeBtn'); if(mb) mb.addEventListener('click',function(){
    var order=['zh','ja','both','all']; setMode(order[(order.indexOf(mode)+1)%4]);
  });
  setMode(mode);
}
/* 复习 */
var reviewState={i:0,res:[]};
function initReview(){
  var box=$('#review'); if(!box)return;
  var cards=JSON.parse(box.getAttribute('data-cards')||'[]');
  var idx=$('#rIdx'), front=$('#rFront'), back=$('#rBack'), bar=$('#rBar');
  if(!cards.length){box.innerHTML='<p class="hint">今天没有到期项。没有就是没有，不编造任务。</p>';return}
  function render(){
    if(reviewState.i>=cards.length){box.innerHTML='<p class="hint">复习完成：'+cards.length+' 张。'+summary()+'</p>';return}
    var c=cards[reviewState.i];
    front.textContent=c.front; back.textContent=c.back;
    back.classList.add('mask');
    idx.textContent=(reviewState.i+1)+' / '+cards.length;
    bar.style.width=Math.round(reviewState.i/cards.length*100)+'%';
  }
  function summary(){var g=reviewState.res.filter(function(x){return x==='good'}).length;
    return ' 记住 '+g+'｜模糊 '+(reviewState.res.filter(function(x){return x==='hard'}).length)+
    '｜忘了 '+(reviewState.res.filter(function(x){return x==='again'}).length)}
  $('#rShow').addEventListener('click',function(){back.classList.toggle('mask')});
  $$('.rRate').forEach(function(b){b.addEventListener('click',function(){
    reviewState.res.push(b.getAttribute('data-rate')); reviewState.i++; render();})});
  render();
}
/* 词卡 */
var vState={i:0,res:{}};
function initVocab(){
  var box=$('#vocab'); if(!box)return;
  var cards=JSON.parse(box.getAttribute('data-cards')||'[]');
  var cur=$('#vCur'), total=$('#vTotal'), area=$('#vArea');
  total.textContent=cards.length;
  function render(){
    if(vState.i>=cards.length){area.innerHTML='<p class="hint">今天的词过完了。没记住的会在明天复习里出现。</p>';return}
    var c=cards[vState.i];
    cur.textContent=vState.i+1;
    var ko=c.ko?'<div class="ko" data-role="zh">朝鲜语汉字词：'+c.ko+'</div>':'';
    var ex=c.ex?'<div class="ex"><span data-role="ja">'+c.ex.ja+'</span><br><span class="zh" data-role="zh">'+c.ex.zh+'</span></div>':'';
    area.innerHTML='<div class="vcard" data-mode="'+mode+'">'+
      '<button class="eye" type="button">切换遮盖</button>'+
      '<div class="surface" data-role="ja">'+c.surface+'</div>'+
      '<div class="kana" data-role="ja">'+c.kana+'</div>'+
      '<div class="meaning" data-role="zh">'+c.meaning+'</div>'+ko+ex+
      (c.audio?'<div class="row" style="margin-top:8px"><button class="btn" data-speak="'+c.surface+'">听发音</button></div>':'')+
      '</div>';
    applyMode(area); initMask();
  }
  $('#vPrev').addEventListener('click',function(){if(vState.i>0){vState.i--;render()}});
  $('#vNext').addEventListener('click',function(){vState.i++;render()});
  $$('#vocab .vRate').forEach(function(b){b.addEventListener('click',function(){
    vState.res[cards[vState.i].id]=b.getAttribute('data-rate'); vState.i++; render();})});
  render();
}
/* 练习：答案只存哈希，不在页面里出现明文 */
var QUIZ_RESULTS=[];
function fnv(t){var s=String(t==null?'':t).normalize('NFKC').replace(/\s+/g,'');
  var h=2166136261>>>0; for (const ch of s){h^=ch.codePointAt(0);h=Math.imul(h,16777619)>>>0;} return h.toString(16);}
function initQuiz(){
  var box=$('#quiz'); if(!box)return;
  var qs=JSON.parse(box.getAttribute('data-qs')||'[]');
  var done=0,right=0;
  var score=$('#score');
  qs.forEach(function(q,qi){
    var wrap=document.createElement('div'); wrap.className='q';
    wrap.innerHTML='<div><strong>'+(qi+1)+'.</strong> '+q.prompt+'</div>';
    var opts=document.createElement('div'); opts.className='opts';
    (q.options||[]).forEach(function(o,oi){
      var lab=document.createElement('label'); lab.className='opt';
      lab.innerHTML='<input type="radio" name="q'+qi+'"><span>'+o+'</span>';
      lab.addEventListener('click',function(){
        if(wrap.getAttribute('data-done'))return;
        wrap.setAttribute('data-done','1');
        var ok=fnv(o)===q.h;
        lab.classList.add(ok?'correct':'wrong');
        if(!ok){ $$('.opt',opts).forEach(function(x,i){ if(q.oh[i]===q.h) x.classList.add('correct'); }); }
        var fb=document.createElement('div'); fb.className='fb '+(ok?'ok':'bad');
        fb.textContent=(ok?'对。':'错。')+(q.rationale||'');
        wrap.appendChild(fb); done++; if(ok)right++;
        score.textContent=right+' / '+done;
        QUIZ_RESULTS.push({qid:q.qid,answer:o,correct:ok,seconds:0,hinted:false,revealed_before_submit:false});
      });
      opts.appendChild(lab);
    });
    wrap.appendChild(opts);
    box.appendChild(wrap);
  });
}
/* 句子草稿 */
function initSentences(){
  var box=$('#sentences'); if(!box)return;
  var items=JSON.parse(box.getAttribute('data-items')||'[]');
  items.forEach(function(s,i){
    var d=document.createElement('div'); d.className='q';
    d.innerHTML='<div class="small">'+(s.direction==='zh-ja'?'中 → 日':'日 → 中')+'　'+(s.hint||'')+'</div>'+
      '<div style="font-size:17px;margin:4px 0">'+s.prompt+'</div>'+
      '<textarea data-k="'+s.id+'" placeholder="先自己写，会话里逐句改"></textarea>';
    box.appendChild(d);
    var ta=$('textarea',d);
    ta.value=localStorage.getItem(STORE+'s.'+s.id)||'';
    ta.addEventListener('input',function(){localStorage.setItem(STORE+'s.'+s.id,ta.value)});
  });
}
/* 朗读 */
function initSpeak(){
  document.addEventListener('click',function(e){
    var b=e.target.closest('[data-speak]'); if(!b)return;
    if(!window.speechSynthesis)return;
    var u=new SpeechSynthesisUtterance(b.getAttribute('data-speak'));
    u.lang='ja-JP'; u.rate=0.95; speechSynthesis.cancel(); speechSynthesis.speak(u);
  });
}
/* 同步：只发原始事件，不发 correct */
function sync(payload){
  try{
    if(location.protocol!=='http:'&&location.protocol!=='https:')return;
    fetch('/api/events',{method:'POST',headers:{'content-type':'application/json'},
      body:JSON.stringify(payload),keepalive:true}).catch(function(){});
  }catch(e){}
}
document.addEventListener('DOMContentLoaded',function(){
  initMask(); initReview(); initVocab(); initQuiz(); initSentences(); initSpeak();
  var f=$('#finish');
  if(f)f.addEventListener('click',function(){
    var day=document.body.getAttribute('data-day');
    var payload={v:1,day:Number(day),session:'web-'+day,minutes:42,results:QUIZ_RESULTS,
      review_ratings:Object.keys(vState.res).map(function(k){return {kid:k,rating:vState.res[k]}}),
      sentences:Object.keys(localStorage).filter(function(k){return k.indexOf(STORE+'s.')===0})
        .map(function(k){return {id:k.split('.').pop(),text:localStorage.getItem(k)}})};
    sync(payload);
    f.textContent='已记录，可以进会话了';
    f.disabled=true;
  });
});
})();
"""


HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>Day @@DAY@@ · @@THEME@@ | Nihongo 150</title>
<link rel="icon" href="data:,"><link rel="stylesheet" href="assets/app.css">
</head><body data-day="@@DAY@@">
<header class="top">
  <span class="day">Day @@DAY@@</span>
  <span class="goal">@@CAN_DO@@</span>
  <button class="mode" id="modeBtn" type="button">遮盖：中文</button>
  <span class="prog">@@MIN@@ 分钟</span>
</header>
<div class="wrap">
<nav class="toc">
  <a href="#review">① 复习</a><a href="#vocab">② 新词</a><a href="#grammar">③ 语法</a>
  <a href="#sentences">④ 句子</a><a href="#quiz">⑤ 练习</a>@@TOC_LISTEN@@
</nav>
<main>
<section class="card" id="review">
  <h2>① 今日复习 <span class="min">12 分钟</span></h2>
  <p class="hint">先自己想，再翻面；三档自评。<span id="rIdx"></span></p>
  <div class="vcard"><div class="surface" id="rFront"></div>
    <div class="meaning mask" id="rBack"></div></div>
  <div class="row"><button class="btn" id="rShow" type="button">翻面</button></div>
  <div class="row" style="margin-top:8px">
    <button class="btn rRate" data-rate="again" type="button">忘了</button>
    <button class="btn rRate" data-rate="hard" type="button">模糊</button>
    <button class="btn rRate" data-rate="good" type="button">记住了</button>
  </div>
  <div style="height:4px;background:var(--line);border-radius:2px;margin-top:10px"><div id="rBar" style="height:4px;background:var(--accent);width:0"></div></div>
  <script type="application/json" id="reviewData">@@REVIEW@@</script>
</section>

<section class="card" id="vocab">
  <h2>② 新词 <span class="min">@@VMIN@@ 分钟</span></h2>
  <p class="hint"><span id="vCur">1</span> / <span id="vTotal">0</span>　点「切换遮盖」可遮中文或遮日语。</p>
  <div id="vArea"></div>
  <div class="kstrip">@@KANJI@@</div>
  <div class="row"><button class="btn" id="vPrev" type="button">上一个</button>
    <button class="btn primary" id="vNext" type="button">下一个</button></div>
</section>

<section class="card" id="grammar">
  <h2>③ 语法 <span class="min">7 分钟</span></h2>
  @@GRAMMAR@@
</section>

<section class="card" id="sentences">
  <h2>④ 句子输出 <span class="min">6 分钟</span></h2>
  <p class="hint">先自己写，不判对错；会话里逐句改。草稿自动保存。</p>
  <div id="sentences"></div>
</section>

<section class="card" id="quiz">
  <h2>⑤ 练习 <span class="min">6 分钟</span></h2>
  <p class="hint">即时判分。当前：<strong id="score">0 / 0</strong></p>
  <div id="quiz"></div>
</section>
@@LISTEN@@
<button class="btn primary" id="finish" type="button" style="width:100%;margin-top:16px">今天学完了，记录一下</button>
<p class="small" style="margin-top:12px">资源骨架来自 OpenJLPT（CC-BY-SA-4.0），中文释义与翻译为 AI 草稿；无真人录音时用浏览器 TTS，已标注 tts。</p>
</main>
</div>
<script>window.__REVIEW__=@@REVIEW@@;window.__VOCAB__=@@VOCAB__;window.__QUIZ__=@@QUIZ__;window.__SENT__=@@SENT__;</script>
<script src="assets/app.js"></script>
<script>
document.getElementById('review').setAttribute('data-cards',JSON.stringify(window.__REVIEW__));
document.getElementById('vocab').setAttribute('data-cards',JSON.stringify(window.__VOCAB__));
document.getElementById('quiz').setAttribute('data-qs',JSON.stringify(window.__QUIZ__));
document.getElementById('sentences').setAttribute('data-items',JSON.stringify(window.__SENT__));
</script>
</body></html>
"""


def fnv(text):
    """与前端一致的 FNV-1a（按 Unicode 码点），用于避免把答案明文写进 HTML。"""
    h = 2166136261
    import re as _re
    import unicodedata as _ud
    for ch in _re.sub(r"\s+", "", _ud.normalize("NFKC", str(text))):
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return format(h, "x")


def build_quiz(day, vocab, grammar, kanji, rnd):
    """按当天新词/汉字/语法出 6 题，保证与课程对齐；答案只存哈希。"""
    import random as _r
    qs = []
    vids = list(day["new_vocab_ids"])
    kids = list(day["new_kanji_ids"])
    gids = list(day["new_grammar_ids"])
    pool = [v for k, v in vocab.items() if v.get("meaning_zh")]

    def add(prompt, options, answer, rationale, qid):
        opts = list(dict.fromkeys([o for o in options if o]))
        if answer not in opts:
            opts.insert(0, answer)
        opts = opts[:4]
        rnd.shuffle(opts)
        qs.append({"qid": qid, "prompt": prompt, "options": opts,
                   "h": fnv(answer), "oh": [fnv(o) for o in opts],
                   "rationale": rationale})

    for vid in vids[:3]:
        v = vocab[vid]
        distract = [x["meaning_zh"] for x in rnd.sample(
            [x for x in pool if x["id"] != vid and x.get("jlpt") == v.get("jlpt")], 3)] if len(pool) > 4 else []
        add("「%s」是什么意思？" % v["surface"], [v["meaning_zh"]] + distract, v["meaning_zh"],
            "%s（%s）＝%s" % (v["surface"], v["kana"], v["meaning_zh"]), "Q-%03d-V%d" % (day["day"], len(qs)))
    for kid in kids[:1]:
        k = kanji[kid]
        correct = (k.get("onyomi") or k.get("kunyomi") or [""])[0]
        if not correct:
            continue
        others = []
        for x in rnd.sample([y for y in kanji.values() if y.get("onyomi") or y.get("kunyomi")], 8):
            r = (x.get("onyomi") or x.get("kunyomi") or [""])[0]
            if r and r != correct:
                others.append(r)
        add("汉字「%s」的读音是？" % k["char"], [correct] + others[:3], correct,
            "%s：音 %s｜训 %s" % (k["char"], "、".join(k.get("onyomi") or []) or "无",
                                 "、".join(k.get("kunyomi") or []) or "无"),
            "Q-%03d-K" % day["day"])
    for gid in gids[:1]:
        g = grammar[gid]
        others = [x["meaning_zh"] for x in rnd.sample(
            [y for y in grammar.values() if y.get("meaning_zh") and y["id"] != gid], 3)]
        add("句型「%s」的意思是？" % g["pattern"], [g["meaning_zh"]] + others, g["meaning_zh"],
            "%s＝%s" % (g["pattern"], g["meaning_zh"]), "Q-%03d-G" % day["day"])
    # 用复习词补足 6 题
    for vid in (day.get("review_knowledge_ids") or []):
        if len(qs) >= 6:
            break
        v = vocab.get(vid)
        if not v or not v.get("meaning_zh"):
            continue
        distract = [x["meaning_zh"] for x in rnd.sample(
            [x for x in pool if x["id"] != vid], 3)]
        add("复习：「%s」是什么意思？" % v["surface"], [v["meaning_zh"]] + distract,
            v["meaning_zh"], "%s＝%s" % (v["surface"], v["meaning_zh"]), "Q-%03d-R" % day["day"])
    return qs[:6]


def build_review(day, vocab, grammar):
    """从 state.db 读到期卡；没有就用当天 review_knowledge_ids 生成预习卡。"""
    cards = []
    db = ROOT / "data/state.db"
    if db.is_file():
        try:
            import sqlite3
            conn = sqlite3.connect(db)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT knowledge_id, due, stage FROM fsrs_cards WHERE due <= datetime('now') "
                "ORDER BY due LIMIT 80").fetchall()
            for r in rows:
                kid = r["knowledge_id"].split("|")[0]
                if kid in vocab:
                    cards.append({"kid": kid, "front": vocab[kid]["surface"],
                                  "back": vocab[kid]["meaning_zh"], "stage": r["stage"]})
                elif kid in grammar:
                    cards.append({"kid": kid, "front": grammar[kid]["pattern"],
                                  "back": grammar[kid]["meaning_zh"], "stage": r["stage"]})
            conn.close()
        except Exception:
            cards = []
    if not cards:
        for kid in day.get("review_knowledge_ids") or []:
            if kid in vocab:
                cards.append({"kid": kid, "front": vocab[kid]["surface"],
                              "back": vocab[kid]["meaning_zh"], "stage": "planned"})
            elif kid in grammar:
                cards.append({"kid": kid, "front": grammar[kid]["pattern"],
                              "back": grammar[kid]["meaning_zh"], "stage": "planned"})
    return cards[:80]


def build_grammar_html(day, grammar):
    out = []
    for gid in day["new_grammar_ids"]:
        g = grammar[gid]
        exs = "".join(
            '<div class="ex"><span data-role="ja">%s</span><br><span class="zh" data-role="zh">%s</span></div>'
            % (esc(e.get("ja")), esc(e.get("zh"))) for e in (g.get("examples") or [])[:3])
        err = (g.get("common_errors") or [{}])[0]
        ko = ""
        if g.get("ko_equiv"):
            ko = ('<div class="ko-box"><strong>朝鲜语：</strong>%s<br><span class="small">%s</span></div>'
                  % (esc(g["ko_equiv"]), esc(g.get("ko_diff", ""))))
        out.append(
            '<div class="gcard" data-mode="all"><button class="eye" type="button">切换遮盖</button>'
            '<div class="pattern" data-role="ja">%s</div>'
            '<div class="conn" data-role="ja">%s</div>'
            '<div class="meaning" data-role="zh">%s</div>'
            '<p class="small">%s</p>%s%s%s</div>'
            % (esc(g["pattern"]), esc(g.get("connection", "")), esc(g["meaning_zh"]),
               esc(g.get("usage", "")), exs, ko,
               ('<p class="small">易错：%s → %s（%s）</p>' %
                (esc(err.get("wrong")), esc(err.get("fix")), esc(err.get("why"))))
               if err.get("wrong") else ""))
    return "".join(out) or '<p class="hint">今天没有新语法。</p>'


def main():
    cur = json.loads((ROOT / "curriculum/curriculum.json").read_text(encoding="utf-8"))
    vocab = {x["id"]: x for x in read("vocabulary.jsonl")}
    grammar = {x["id"]: x for x in read("grammar.jsonl")}
    kanji = {x["id"]: x for x in read("kanji.jsonl")}
    materials = {x["id"]: x for x in read("materials.jsonl")}
    questions = {x["id"]: x for x in read("questions.jsonl")}
    sentences = defaultdict(list)
    for s in read("sentences.jsonl"):
        sentences[s["day"]].append(s)

    OUT.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    (OUT / "assets/app.css").write_text(CSS, encoding="utf-8")
    (OUT / "assets/app.js").write_text(JS, encoding="utf-8")

    for d in cur["days"]:
        n = d["day"]
        vcards = []
        for vid in d["new_vocab_ids"]:
            v = vocab[vid]
            ex = (v.get("examples") or [{}])[0]
            vcards.append({
                "id": vid, "surface": v["surface"], "kana": v["kana"], "meaning": v["meaning_zh"],
                "ko": v.get("ko_hanja") or "", "pos": v.get("pos", ""),
                "ex": {"ja": ex.get("ja", ""), "zh": ex.get("zh", "")} if ex.get("ja") else None,
                "audio": None,
            })
        import random as _random
        qs = build_quiz(d, vocab, grammar, kanji, _random.Random(20261107 + n))
        # 汉字小条：放在新词块末尾，不单独占一块
        kanji_html = "".join(
            '<span class="kchip"><strong>%s</strong> %s <span class="small">%s</span></span>'
            % (esc(kanji[k]["char"]), esc(kanji[k]["meaning_zh"]),
               esc("、".join((kanji[k].get("onyomi") or []) + (kanji[k].get("kunyomi") or []))[:2]))
            for k in d["new_kanji_ids"])
        review = build_review(d, vocab, grammar)
        listen_html = ""
        listen_json = None
        if d.get("listening"):
            mids = d.get("material_ids") or []
            m = materials.get(mids[0]) if mids else None
            if m:
                listen_json = {"id": m["id"], "title": m.get("title", ""), "audio_url": m.get("audio_url"),
                               "audio_kind": m.get("audio_kind", "tts"),
                               "transcript": m.get("text_ja", "")[:1200],
                               "duration_sec": m.get("duration_sec", 0)}
                listen_html = (
                    '<section class="card" id="listening"><h2>⑥ 听力 <span class="min">8 分钟</span></h2>'
                    '<p class="hint">先听，再答题；脚本做完再展开。</p>'
                    '<div class="row"><button class="btn" type="button" data-speak="%s">播放（TTS）</button></div>'
                    '<details><summary>看脚本</summary><p data-role="ja">%s</p></details></section>'
                    % (esc(listen_json["transcript"][:400]), esc(listen_json["transcript"])))
        page = (HTML
                .replace("@@DAY@@", "%03d" % n)
                .replace("@@THEME@@", esc(d["theme"]))
                .replace("@@CAN_DO@@", esc(d["can_do"]))
                .replace("@@MIN@@", str(d["minutes"]))
                .replace("@@VMIN@@", "8" if d.get("listening") else "14")
                .replace("@@TOC_LISTEN@@", '<a href="#listening">⑥ 听力</a>' if d.get("listening") else "")
                .replace("@@GRAMMAR@@", build_grammar_html(d, grammar))
                .replace("@@KANJI@@", kanji_html).replace("@@LISTEN@@", listen_html)
                .replace("@@REVIEW@@", json.dumps(review, ensure_ascii=False))
                .replace("@@VOCAB__", json.dumps(vcards, ensure_ascii=False))
                .replace("@@VOCAB__", json.dumps(vcards, ensure_ascii=False))
                .replace("@@QUIZ__", json.dumps(qs, ensure_ascii=False))
                .replace("@@SENT__", json.dumps(sentences.get(n, []), ensure_ascii=False)))
        # 上面的占位符写法要严格匹配
        page = page.replace("@@VOCAB__", json.dumps(vcards, ensure_ascii=False))
        (OUT / ("day-%03d.html" % n)).write_text(page, encoding="utf-8")
        (DATA / ("day-%03d.json" % n)).write_text(json.dumps({
            "day": n, "phase": d["phase"], "theme": d["theme"], "can_do": d["can_do"],
            "minutes": d["minutes"], "listening": bool(d.get("listening")),
            "review": review, "vocab": vcards, "grammar": [grammar[g] for g in d["new_grammar_ids"]],
            "sentences": sentences.get(n, []), "quiz": qs, "listening_material": listen_json,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # 首页：只做索引，不做统计
    links = "".join('<li><a href="day-%03d.html">Day %03d · %s</a></li>' % (d["day"], d["day"], esc(d["theme"]))
                    for d in cur["days"])
    (OUT / "index.html").write_text(
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Nihongo 150</title><link rel="stylesheet" href="assets/app.css"></head>'
        '<body><div class="wrap"><main><h1>Nihongo 150</h1>'
        '<p class="hint">每天 60 分钟：复习 / 新词 / 语法 / 句子 / 练习。听力 Day 46 起，每周 3 次。</p>'
        '<ul>' + links + '</ul></main></div></body></html>', encoding="utf-8")

    (OUT / "sw.js").write_text(
        "const C='nh80-v5';self.addEventListener('install',e=>{self.skipWaiting()});"
        "self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all("
        "k.filter(x=>x!==C).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))});"
        "self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;"
        "e.respondWith(caches.match(e.request).then(h=>h||fetch(e.request).then(r=>{"
        "if(r.ok&&r.type==='basic'){let c=r.clone();caches.open(C).then(x=>x.put(e.request,c))}return r"
        "}).catch(()=>new Response('离线',{status:503}))))});", encoding="utf-8")
    print(json.dumps({"days": len(cur["days"]), "html": len(list(OUT.glob("day-*.html")))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
