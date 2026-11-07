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
.top .goal{color:var(--muted);font-size:13px;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.top .prog{width:100%;font-variant-numeric:tabular-nums;color:var(--accent);font-weight:700;font-size:13px}
.mode{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;
padding:6px 12px;font-size:13px;cursor:pointer}
section.card{scroll-margin-top:132px;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
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
.ko-box{background:var(--bg);border:1px solid var(--line);padding:8px 10px;margin:8px 0;font-size:14px}
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
.kchip{max-width:100%;overflow-wrap:anywhere;font-size:14px;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:4px 8px}
@media(min-width:1024px){
 section.card{scroll-margin-top:72px}
 .wrap{max-width:1120px;display:grid;grid-template-columns:200px minmax(0,760px);gap:24px;align-items:start}
 nav.toc{position:sticky;top:64px;font-size:14px}
 nav.toc a{display:block;padding:6px 0;color:var(--muted);text-decoration:none}
 main{grid-column:2}
 .foot{position:static;background:none;border:0;justify-content:flex-start;margin-top:8px}
}
audio{width:100%;margin:10px 0} .passage{white-space:pre-line;padding:12px;background:var(--bg);border-radius:8px;margin-bottom:10px}
button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
::selection{background:var(--accent);color:var(--surface)}
.resource-link{display:block;padding:8px 0} .week-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}}
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
if('serviceWorker' in navigator&&location.protocol.startsWith('http'))navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).catch(function(){});
var STORE='nh80.v5.';
function safe(t){return String(t==null?'':t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
var LATEST_PAYLOAD=null;
var mode=localStorage.getItem(STORE+'mode')||'zh';  // all|zh|ja|both
function $(s,r){return (r||document).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))}
function applyMode(root){
  $$('[data-role]',root).forEach(function(el){
    var role=el.getAttribute('data-role');
    var override=el.closest('[data-mode]');var active=override?override.getAttribute('data-mode'):mode;
    var hide=(active==='both')||(active==='zh'&&role==='zh')||(active==='ja'&&role==='ja');
    el.classList.toggle('mask',hide);
    el.classList.toggle('peek',!hide&&el.classList.contains('peek'));
    if(!hide) el.classList.remove('mask');
  });
  var b=$('#modeBtn'); if(b) b.textContent={all:'遮盖：关',zh:'遮盖：中文',ja:'遮盖：日语',both:'遮盖：双向'}[mode];
}
function setMode(m){mode=m;$$('[data-mode]').forEach(function(c){c.setAttribute('data-mode',m)});localStorage.setItem(STORE+'mode',m);applyMode(document)}
var MASK_BOUND=false;
function initMask(){
  applyMode(document);
  if(MASK_BOUND)return;
  MASK_BOUND=true;
  document.addEventListener('click',function(e){
    var mb=e.target.closest('#modeBtn');
    if(mb){var order=['zh','ja','both','all'];setMode(order[(order.indexOf(mode)+1)%4]);return;}
    var eye=e.target.closest('.eye');
    if(eye){
      var card=eye.closest('.vcard,.gcard,.ex');
      if(card){
        var seq=['all','zh','ja','both'];
        var cur=card.getAttribute('data-mode')||mode;
        var next=seq[(seq.indexOf(cur)+1)%4];
        card.setAttribute('data-mode',next);
        $$('[data-role]',card).forEach(function(el){
          var r=el.getAttribute('data-role');
          var hide=(next==='both')||(next==='zh'&&r==='zh')||(next==='ja'&&r==='ja');
          el.classList.toggle('mask',hide); if(!hide)el.classList.remove('peek');
        });
      }
      return;
    }
    var m=e.target.closest('.mask');
    if(m){m.classList.add('peek');setTimeout(function(){m.classList.remove('peek')},3000);}
  });
}
/* 复习 */
var reviewState={i:0,res:[]};
function initReview(){
  var box=$('#review'); if(!box)return;
  var cards=JSON.parse(box.getAttribute('data-cards')||'[]');
  var idx=$('#rIdx'), front=$('#rFront'), back=$('#rBack'), bar=$('#rBar');
  if(!cards.length){box.querySelectorAll('.vcard,.row').forEach(function(e){e.hidden=true});idx.textContent='暂无到期项';return}
  function render(){
    if(reviewState.i>=cards.length){box.querySelectorAll('.vcard,.row').forEach(function(x){x.hidden=true});idx.textContent='复习完成：'+cards.length+' 张。'+summary();return}
    var c=cards[reviewState.i];
    front.textContent=c.front; back.textContent=c.back;
    back.classList.add('mask');
    idx.textContent=(reviewState.i+1)+' / '+cards.length;
    bar.style.width=Math.round(reviewState.i/cards.length*100)+'%';
  }
  function summary(){var g=reviewState.res.filter(function(x){return x.rating==='good'}).length;
    return ' 记住 '+g+'｜模糊 '+(reviewState.res.filter(function(x){return x.rating==='hard'}).length)+
    '｜忘了 '+(reviewState.res.filter(function(x){return x.rating==='again'}).length)}
  $('#rShow').addEventListener('click',function(){back.classList.toggle('mask')});
  $$('.rRate').forEach(function(b){b.addEventListener('click',function(){
    reviewState.res.push({kid:cards[reviewState.i].kid,rating:b.getAttribute('data-rate')}); reviewState.i++; render();})});
  render();
}
/* 词卡 */
var vState={i:0,res:{}};
function initVocab(){
  var box=$('#vocab'); if(!box)return;
  var cards=JSON.parse(box.getAttribute('data-cards')||'[]');
  var coreCards=cards.filter(function(c){return !c.optional});var allCards=cards;cards=coreCards;
  var extra=$('#extraVocab');if(extra)extra.addEventListener('change',function(){cards=extra.checked?allCards:coreCards;vState.i=0;total.textContent=cards.length;render()});
  var cur=$('#vCur'), total=$('#vTotal'), area=$('#vArea');
  total.textContent=cards.length;
  function render(){
    $('#vNext').disabled=vState.i>=cards.length;$('#vPrev').disabled=vState.i<=0;
    if(vState.i>=cards.length){area.innerHTML='<p class="hint">必学词已看完；请在会话中用自己的话造句。</p>';return}
    var c=cards[vState.i];
    cur.textContent=vState.i+1;
    var ko=c.ko?'<div class="ko" data-role="zh">韩语参考'+(c.ko_status==='ai_gloss'?'（AI）':'')+'：'+safe(c.ko)+'</div>':'';
    var ex=c.ex?'<div class="ex"><span data-role="ja">'+safe(c.ex.ja)+'</span><br><span class="zh" data-role="zh">'+safe(c.ex.zh)+'</span></div>':'';
    area.innerHTML='<div class="vcard" data-mode="'+mode+'">'+
      '<button class="eye" type="button">切换遮盖</button>'+
      '<div class="surface" data-role="ja">'+safe(c.surface)+'</div>'+
      '<div class="kana" data-role="ja">'+safe(c.kana)+'</div>'+
      '<div class="meaning" data-role="zh">'+safe(c.meaning)+'</div>'+ko+ex+
      (c.audio?'<div class="row" style="margin-top:8px"><button class="btn" data-speak="'+safe(c.surface)+'">听发音</button></div>':'')+
      '</div>';
    applyMode(area); initMask();
  }
  $('#vPrev').addEventListener('click',function(){if(vState.i>0){vState.i--;render()}});
  $('#vNext').addEventListener('click',function(){if(vState.i<cards.length)vState.i++;render()});
  $$('#vocab .vRate').forEach(function(b){b.addEventListener('click',function(){
    vState.res[cards[vState.i].id]=b.getAttribute('data-rate'); vState.i++; render();})});
  render();
}
/* 练习：答案只存哈希，不在页面里出现明文 */
var QUIZ_RESULTS=[];var STARTED=Date.now();var TRANSCRIPT_HINTED=false;
function fnv(t){var s=String(t==null?'':t).normalize('NFKC').replace(/\s+/g,'');
  var h=2166136261>>>0; for (const ch of s){h^=ch.codePointAt(0);h=Math.imul(h,16777619)>>>0;} return h.toString(16);}
function initQuiz(selector, scoreSelector){
  var box=$(selector); if(!box)return;
  var qs=JSON.parse(box.getAttribute('data-qs')||'[]');
  var done=0,right=0;
  var score=$(scoreSelector);
  qs.forEach(function(q,qi){
    var wrap=document.createElement('div'); wrap.className='q';
    wrap.innerHTML=(q.passage?'<div class="passage" lang="ja">'+safe(q.passage)+'</div>':'')+'<div><strong>'+(qi+1)+'.</strong> '+safe(q.prompt)+'</div>';
    var opts=document.createElement('div'); opts.className='opts';
    (q.options||[]).forEach(function(o,oi){
      var lab=document.createElement('label'); lab.className='opt';
      lab.innerHTML='<input type="radio" name="'+q.qid+'"><span>'+safe(o)+'</span>';
      lab.addEventListener('click',function(){
        if(wrap.getAttribute('data-done'))return;
        wrap.setAttribute('data-done','1');
        var ok=fnv(o)===q.h;
        lab.classList.add(ok?'correct':'wrong');
        if(!ok){ $$('.opt',opts).forEach(function(x,i){ if(q.oh[i]===q.h) x.classList.add('correct'); }); }
        var fb=document.createElement('div'); fb.className='fb '+(ok?'ok':'bad');
        fb.textContent=(ok?'对。':'错，正确项已标绿。')+(q.rationale||'回会话讲清为什么，再造一句自己的话。');
        wrap.appendChild(fb); done++; if(ok)right++;
        score.textContent=right+' / '+done;
        QUIZ_RESULTS.push({qid:q.qid,answer:o,seconds:Math.round((Date.now()-STARTED)/1000),hinted:selector==='#listenQuiz'&&TRANSCRIPT_HINTED,revealed_before_submit:selector==='#listenQuiz'&&TRANSCRIPT_HINTED});
      });
      opts.appendChild(lab);
    });
    wrap.appendChild(opts);
    box.appendChild(wrap);
  });
}
/* 句子草稿 */
function initSentences(){
  var box=$('#sentenceItems'); if(!box)return;
  var items=JSON.parse(box.getAttribute('data-items')||'[]');
  items.forEach(function(s,i){
    var d=document.createElement('div'); d.className='q';if(i===3){var extra=document.createElement('details');extra.innerHTML='<summary>7句选学拓展</summary>';box.appendChild(extra);box=extra;}
    d.innerHTML='<div class="small">'+(i<3?'必做 '+(i+1)+' / 3 · ':'拓展 · ')+(s.direction==='zh-ja'?'中 → 日':'日 → 中')+'　'+safe(s.hint||'')+'</div>'+
      '<div style="font-size:17px;margin:4px 0">'+safe(s.prompt)+'</div>'+
      '<textarea aria-label="句子 '+(i+1)+'译文" data-k="'+s.id+'" placeholder="先自己写，会话里逐句改"></textarea>';
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
    if(!window.speechSynthesis){b.textContent='此设备不支持朗读';return;}
    var u=new SpeechSynthesisUtterance(b.getAttribute('data-speak'));
    u.lang='ja-JP'; u.rate=0.95;var label=b.textContent;u.onerror=function(){b.textContent='设备朗读不可用，请用音频或会话'};u.onend=function(){b.textContent=label}; speechSynthesis.cancel(); speechSynthesis.speak(u);
  });
}
function collectPayload(){
  var day=document.body.getAttribute('data-day');
  return {v:1,day:Number(day),session:sessionStorage.getItem(STORE+'session.'+day)||('web-'+day+'-'+crypto.randomUUID()),minutes:null,ts:new Date().toISOString(),source:'web',results:QUIZ_RESULTS,
      review_ratings:reviewState.res,
      sentences:Object.keys(localStorage).filter(function(k){return k.indexOf(STORE+'s.')===0&&window.__SENT__.some(function(s){return k===STORE+'s.'+s.id})})
        .map(function(k){return {id:k.split('.').pop(),text:localStorage.getItem(k)}})};
}
/* 同步：只发原始事件，不发 correct */
function sync(payload){
  return fetch('/api/events',{method:'POST',headers:{'content-type':'application/json','X-NH80-Key':sessionStorage.getItem(STORE+'access')||''},
    body:JSON.stringify(payload)}).then(function(r){if(!r.ok)throw new Error(r.status===401?'学习口令不正确，请重新输入':r.status===429?'云端保存预算已用完，请导出作答交给老师':'保存暂不可用，请重试或导出作答');return r.json()})
    .then(function(r){if(r.ok!==true)throw new Error('未确认保存');return r});
}
document.addEventListener('DOMContentLoaded',function(){
  initMask(); initReview(); initVocab(); initQuiz('#quizItems','#score'); initQuiz('#listenQuiz','#listenScore');var tr=$('#transcript');if(tr)tr.addEventListener('toggle',function(){if(tr.open)TRANSCRIPT_HINTED=true}); initSentences(); initSpeak();
  var access=$('#accessKey');if(access){access.value=sessionStorage.getItem(STORE+'access')||'';access.addEventListener('input',function(){sessionStorage.setItem(STORE+'access',access.value.trim())})}
  var exportBtn=$('#exportAnswers');if(exportBtn)exportBtn.addEventListener('click',function(){
    var payload=LATEST_PAYLOAD||collectPayload();
    if(!payload){$('#saveStatus').textContent='先作答，再点击保存或导出。';return}
    var url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));var a=document.createElement('a');a.href=url;a.download='nihongo-day-'+payload.day+'.json';a.click();URL.revokeObjectURL(url);
  });
  var f=$('#finish');
  if(f)f.addEventListener('click',function(){
    var day=document.body.getAttribute('data-day');
    var payload=collectPayload();
    var pendingKey=STORE+'pending.'+day;
    var old=localStorage.getItem(pendingKey);
    if(old){try{
      var saved=JSON.parse(old);var valid=window.__QUIZ__.concat(window.__LISTEN__||[]).map(function(q){return q.qid});
      var stale=(saved.results||[]).filter(function(x){return valid.indexOf(x.qid)<0});
      if(stale.length){localStorage.setItem(STORE+'archive.'+day+'.'+Date.now(),old);$('#saveStatus').textContent='旧版作答已另存本机；本页按新版题目保存。'}
      payload.session=stale.length?payload.session:saved.session;
      payload.results=(saved.results||[]).filter(function(x){return valid.indexOf(x.qid)>=0&&!payload.results.some(function(y){return y.qid===x.qid})}).concat(payload.results);
      payload.review_ratings=(saved.review_ratings||[]).filter(function(x){return !payload.review_ratings.some(function(y){return y.kid===x.kid})}).concat(payload.review_ratings);
    }catch(e){}}
    LATEST_PAYLOAD=payload;
    sessionStorage.setItem(STORE+'session.'+day,payload.session);
    localStorage.setItem(pendingKey,JSON.stringify(payload));
    f.disabled=true;f.textContent='正在保存…';
    sync(payload).then(function(){localStorage.removeItem(pendingKey);f.textContent='已保存，进入会话批改三句';$('#saveStatus').textContent='作答已同步；整天完成须教师核对自主输出。';localStorage.setItem(STORE+'lastDay',day);})
    .catch(function(e){f.disabled=false;f.textContent='保存失败，点击重试';$('#saveStatus').textContent=e.message+'。作答已暂存此设备。';});
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
  <span class="goal" title="@@CAN_DO@@">@@THEME@@</span>
  <button class="mode" id="modeBtn" type="button">遮盖：中文</button>
  <span class="prog">网页 42 分钟 · 会话 18 分钟</span>
</header>
<div class="wrap">
<nav class="toc">
  <a href="#review">① 复习</a><a href="#vocab">② 新词</a><a href="#grammar">③ 语法</a>
  @@TOC_LISTEN@@<a href="#sentences">@@SNUM@@ 句子</a><a href="#quiz">@@QNUM@@ 练习</a>
</nav>
<main>
<p class="hint">@@CAN_DO@@</p><p class="small"><a href="/">课程目录</a> · <a href="resources.html">官方真人听力与N3样题</a></p>
<section class="card" id="review">
  <h2>① 今日复习 <span class="min">@@RMIN@@ 分钟</span></h2>
  <p class="hint">课程复习词：先想再翻面；会话再核对权威到期队列。<span id="rIdx"></span></p>
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
  <label class="small"><input id="extraVocab" type="checkbox"> 包含选学拓展（@@EXTRA_COUNT@@词）</label>
  <div id="vArea"></div>
  <div class="kstrip">@@KANJI@@</div>
  <div class="row"><button class="btn" id="vPrev" type="button">上一个</button>
    <button class="btn primary" id="vNext" type="button">下一个</button></div>
</section>

<section class="card" id="grammar">
  <h2>③ 语法 <span class="min">@@GMIN@@ 分钟</span></h2>
  @@GRAMMAR@@
</section>

@@LISTEN@@
<section class="card" id="sentences">
  <h2>@@SNUM@@ 句子输出 <span class="min">@@SMIN@@ 分钟</span></h2>
  <p class="hint">先完成3句，会话里逐句改；其余7句可选。草稿自动保存在此设备。</p>
  <div id="sentenceItems"></div>
</section>

<section class="card" id="quiz">
  <h2>@@QNUM@@ 练习 <span class="min">@@QMIN@@ 分钟</span></h2>
  <p class="hint">即时判分。当前：<strong id="score">0 / 0</strong></p>
  <div id="quizItems"></div>
</section>
<details><summary>云端保存设置（仅首次）</summary><label class="small">学习口令 <input id="accessKey" type="password" autocomplete="off" placeholder="个人学习口令"></label><p class="small">口令只保留在当前标签页；未输入时也可导出作答交给老师。</p></details>
<p id="saveStatus" class="small" role="status" aria-live="polite"></p><button class="btn" type="button" id="exportAnswers">导出作答</button>
<button class="btn primary" id="finish" type="button" style="width:100%;margin-top:16px">今天学完了，记录一下</button>
<p class="small" style="margin-top:12px"><a href="resources.html">官方真人听力、样题与资源署名</a> · 原创文本合成语音；内容包含 AI 草稿。</p>
</main>
</div>
<script>window.__REVIEW__=@@REVIEW@@;window.__VOCAB__=@@VOCAB__;window.__QUIZ__=@@QUIZ__;window.__SENT__=@@SENT__;window.__LISTEN__=@@LQS@@;</script>
<script src="assets/app.js"></script>
<script>
document.getElementById('review').setAttribute('data-cards',JSON.stringify(window.__REVIEW__));
document.getElementById('vocab').setAttribute('data-cards',JSON.stringify(window.__VOCAB__));
document.getElementById('quizItems').setAttribute('data-qs',JSON.stringify(window.__QUIZ__));
document.getElementById('sentenceItems').setAttribute('data-items',JSON.stringify(window.__SENT__));
</script>
</body></html>
"""


from quiz_v5 import fnv, build_quiz, listening_quiz, public_question, day_questions


def build_review(day, vocab, grammar):
    """公开页面只放课程复习词；权威到期队列由私人会话读取，避免公开学习状态。"""
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
    audio_manifest_path = OUT / "audio/manifest.json"
    audio_manifest = json.loads(audio_manifest_path.read_text()) if audio_manifest_path.exists() else {"items": {}}
    import hashlib

    sentences = defaultdict(list)
    for s in read("sentences.jsonl"):
        sentences[s["day"]].append({k: v for k, v in s.items() if not k.startswith("answer")})

    if not OUT.is_dir():
        OUT.mkdir(parents=True)
    (DATA / "answer-key.json").unlink(missing_ok=True)
    (OUT / "404.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>页面未找到</title><h1>页面未找到</h1><a href="/">返回课程目录</a></html>', encoding="utf-8")
    if not DATA.is_dir():
        DATA.mkdir(parents=True)
    if not (OUT / "assets").is_dir():
        (OUT / "assets").mkdir(parents=True)
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
                "ko": v.get("ko_hint") or v.get("ko_hanja") or "", "ko_status": v.get("ko_status"), "optional": vid in d.get("extension_vocab_ids", []), "pos": v.get("pos", ""),
                "ex": {"ja": ex.get("ja", ""), "zh": ex.get("zh", "")} if ex.get("ja") else None,
                "audio": "tts",
            })
        import random as _random
        qs = [public_question(q) for q in day_questions(d, vocab, grammar, kanji, materials) if not q["qid"].startswith("L-")]
        # 汉字小条：放在新词块末尾，不单独占一块
        kanji_html = "".join(
            '<details class="kchip"><summary><strong>%s</strong> %s</summary>'
            '<p class="small">音读：%s<br>训读：%s<br>韩语字音：%s<br>%s<br>%s</p></details>'
            % (esc(kanji[k]["char"]), esc(kanji[k]["meaning_zh"]),
               esc("、".join(kanji[k].get("onyomi") or []) or "无常用音读"),
               esc("、".join(kanji[k].get("kunyomi") or []) or "无常用训读"),
               esc(kanji[k].get("ko_hanja") or ""), esc(kanji[k].get("ko_note") or ""),
               esc(kanji[k].get("zh_trap") or "按词语核对实际读音，不把单字读音机械拼词。"))
            for k in d["new_kanji_ids"])
        review = build_review(d, vocab, grammar)
        listen_html = ""
        listen_json = None
        if d.get("listening"):
            mids = d.get("material_ids") or []
            m = materials.get(mids[0]) if mids else None
            if m:
                lqs = [public_question(q) for q in listening_quiz(d, m)]
                audio = audio_manifest.get("items", {}).get(m["id"], {})
                valid_audio = (audio.get("text_sha256") == hashlib.sha256(m["audio_text"].encode()).hexdigest()
                               and (OUT / str(audio.get("url", "")).lstrip("/")).is_file())
                if not valid_audio:
                    raise ValueError("缺少匹配原稿的完整音频：" + m["id"])
                listen_json = {"id": m["id"], "title": m["title"], "audio_url": audio["url"],
                               "audio_kind": "synthetic", "transcript": m["text_ja"],
                               "duration_sec": audio["duration_sec"], "questions": lqs}
                listen_html = (
                    '<section class="card" id="listening"><h2>④ 听力 <span class="min">8 分钟</span></h2>'
                    '<p class="hint">原创文本 · Kokoro 合成语音 · %s秒。先听，再答三题。</p>'
                    '<audio controls preload="metadata" src="%s" aria-label="当天听力"></audio>'
                    '<details><summary>音频无法播放时</summary><button class="btn" type="button" data-speak="%s">设备朗读（TTS）</button></details>'
                    '<div id="listenQuiz" data-qs="%s"></div><p>得分：<span id="listenScore">0 / 0</span></p>'
                    '<details id="transcript"><summary>看脚本（计为提示）</summary><p lang="ja">%s</p></details></section>'
                    % (round(audio["duration_sec"], 1), esc(audio["url"]), esc(m["audio_text"]),
                       esc(json.dumps(lqs, ensure_ascii=False)), esc(m["text_ja"])))
        budget = {b["type"]: b["min"] for b in d["blocks"]}
        page = (HTML
                .replace("@@DAY@@", "%03d" % n)
                .replace("@@EXTRA_COUNT@@", str(len(d.get("extension_vocab_ids", []))))
                .replace("@@LQS@@", json.dumps(listen_json["questions"] if listen_json else [], ensure_ascii=False))
                .replace("@@THEME@@", esc(d["theme"]))
                .replace("@@CAN_DO@@", esc(d["can_do"]))
                .replace("@@MIN@@", str(d["minutes"]))
                .replace("@@VMIN@@", str(budget["新词"]))
                .replace("@@RMIN@@", str(budget["复习"]))
                .replace("@@GMIN@@", str(budget["语法"]))
                .replace("@@SMIN@@", str(budget["句子输出"]))
                .replace("@@QMIN@@", str(budget["练习"]))
                .replace("@@SNUM@@", "⑤" if d.get("listening") else "④")
                .replace("@@QNUM@@", "⑥" if d.get("listening") else "⑤")
                .replace("@@TOC_LISTEN@@", '<a href="#listening">④ 听力</a>' if d.get("listening") else "")
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
            "minutes": d["minutes"], "blocks": d["blocks"], "listening": bool(d.get("listening")),
            "review": review, "vocab": vcards, "core_vocab_ids": d.get("core_vocab_ids"), "extension_vocab_ids": d.get("extension_vocab_ids"), "grammar": [grammar[g] for g in d["new_grammar_ids"]],
            "sentences": sentences.get(n, []), "quiz": qs, "listening_material": listen_json,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    (OUT / "n3-mock.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>N3 自测入口</title><h1>N3 自测</h1><p>使用官方样题，答后对照答案。本站阶段练习不换算官方分数。</p><a href="resources.html">打开官方听力、阅读与样题</a></html>',encoding="utf-8")
    (OUT / "manifest.webmanifest").write_text(json.dumps({"name":"Nihongo 150","short_name":"Nihongo","start_url":"/","display":"standalone","background_color":"#fbfaf7","theme_color":"#b4472e","icons":[{"src":"/icon.svg","sizes":"any","type":"image/svg+xml"}]},ensure_ascii=False),encoding="utf-8")
    # 首页：只做索引，不做统计
    links = '<p><a id="resume" class="btn primary" href="day-001.html">开始或继续学习</a></p><p><a href="resources.html">N3 官方样题、真人听力与阅读资源</a></p>'
    for start in range(1, 151, 7):
        chunk = [d for d in cur["days"] if start <= d["day"] < start + 7]
        links += '<details%s><summary>第 %d 周 · Day %d–%d</summary><ul class="week-grid">%s</ul></details>' % (
            ' open' if start == 1 else '', (start-1)//7+1, start, chunk[-1]["day"],
            ''.join('<li><a href="day-%03d.html">Day %03d · %s</a></li>' % (d["day"],d["day"],esc(d["theme"])) for d in chunk))
    (OUT / "index.html").write_text(
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Nihongo 150</title><link rel="stylesheet" href="assets/app.css"></head>'
        '<body><div class="wrap"><main><h1>Nihongo 150</h1>'
        '<p class="hint">每天 60 分钟：复习 / 新词 / 语法 / 句子 / 练习。听力 Day 47 起，每周 3 次。</p>'
        + links + '</main></div><script>var n=Number(localStorage.getItem("nh80.v5.lastDay")||1);if(n>=1&&n<=150){document.getElementById("resume").href="day-"+String(n).padStart(3,"0")+".html";}</script></body></html>', encoding="utf-8")

    resource_data = json.loads((ROOT / "knowledge/resources.json").read_text())
    resources_html = '<h1>N3 学习资源</h1><p>先完成每日必学，再按阶段使用官方样题检查。外部材料只在原站使用。</p>'
    for resource in resource_data["resources"]:
        resources_html += '<section class="card"><h2><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></h2><p>%s</p><p class="small">%s</p></section>' % (esc(resource["url"]),esc(resource["title"]),esc(resource["usage"]),esc(resource["license"]))
    resources_html += '<p><a href="library.html">更多原创短文与听读练习</a> · <a href="audio/NOTICE.txt">完整音频署名与许可声明</a></p><h2>本地内容与署名</h2><p class="small">词汇等资源来自 OpenJLPT（CC BY-SA 4.0）；韩语词典字段来自韩国国立国语院 한국어기초사전（CC BY-SA 2.0 KR），词典整理项目 spellcheck-ko/korean-dict-nikl。未匹配字段为标注的 AI 韩语释义。不同词在语境中并非总能互换。汉字韩语字音补充来自 EDRDG KANJIDIC2（<a href="https://www.edrdg.org/wiki/index.php/KANJIDIC_Project">项目与许可</a>），字音参考不能机械拼成韩语词。</p><p class="small">原创文本合成音频：<a href="https://huggingface.co/hexgrad/Kokoro-82M">Kokoro-82M</a>（Apache-2.0，jf_alpha），日语处理使用 The UniDic Consortium 的 UniDic 3.1.0（BSD选项），源字典由原作者保留版权；工具使用 Misaki 和 Open JTalk。本站不重新分发官方试题、第三方真人录音或系统内置声音。</p>'
    (OUT / "resources.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>N3 学习资源</title><link rel="stylesheet" href="assets/app.css"><div class="wrap" style="display:block;max-width:760px"><a href="/">返回课程</a>'+resources_html+'</div></html>',encoding="utf-8")
    library = '<h1>原创听读资料</h1><p>按级别选一篇。先理解大意，再看译文；短篇可用设备朗读。</p>'
    for level in ("N5", "N4", "N3"):
        library += '<h2>'+level+'</h2>'
        for m in materials.values():
            if m.get("level") != level or m.get("license") != "original" or not m.get("text_ja"):
                continue
            _a = audio_manifest.get("items", {}).get(m["id"])
            _audio = ('<audio controls preload="none" src="%s" aria-label="%s"></audio><p class="small">合成语音 · %s 秒</p>'
                      % (esc(_a["url"]), esc(m["title"]), round(_a["duration_sec"], 1))) if _a else ''
            library += '<details><summary>%s · %s</summary>%s<p lang="ja" class="passage">%s</p><button class="btn" data-speak="%s">设备朗读</button><details><summary>中文参考</summary><p>%s</p></details></details>' % (esc(m["id"]),esc(m["title"]),_audio,esc(m["text_ja"]),esc(m["audio_text"]),esc(m.get("text_zh") or "请先独立理解，再交会话答疑。"))
    (OUT / "library.html").write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>原创听读资料</title><link rel="stylesheet" href="assets/app.css"><div class="wrap" style="display:block;max-width:760px"><a href="resources.html">返回官方资源</a>'+library+'</div><script src="assets/app.js"></script></html>',encoding="utf-8")
    import hashlib
    revision = hashlib.sha256((CSS + JS + json.dumps(cur, ensure_ascii=False)).encode()).hexdigest()[:12]
    (OUT / "sw.js").write_text(
        "const C='nh80-v5.1-" + revision + "';self.addEventListener('install',e=>self.skipWaiting());"
        "self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(ks=>Promise.all("
        "ks.filter(k=>k!==C).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));"
        "self.addEventListener('fetch',e=>{if(e.request.method!=='GET'||new URL(e.request.url).origin!==location.origin||new URL(e.request.url).pathname.startsWith('/api/'))return;"
        "e.respondWith(fetch(e.request).then(r=>{if(r.ok){const c=r.clone();e.waitUntil(caches.open(C).then(x=>x.put(e.request,c)))}return r})"
        ".catch(()=>caches.match(e.request).then(r=>r||new Response('离线且本页尚未缓存',{status:503}))));});", encoding="utf-8")
    print(json.dumps({"days": len(cur["days"]), "html": len(list(OUT.glob("day-*.html")))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
