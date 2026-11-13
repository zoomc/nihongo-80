#!/usr/bin/env python3
"""build_v5_site.py — v10 每日页：只留内容。

设计口径（2026-11-08，用户明确要求）：
- 顶部不要模式按钮 / 分钟数 / 分段导航 / 站点链接 / 提示文案；
- 新词与语法各自一个局部遮挡开关；
- 当天新词两题、语法三题，洗牌后一次列出，支持错题重练；
- 新词分日语、中文与韩语读音两列，例句可展开；
- 底部只有一个「完成」按钮，上报当天学习情况到 /api/progress。

构建期生成全部 HTML；前端 app.js 只负责遮挡 / 朗读 / 判分 / 完成上报。
其余页面（首页、资源页、真人听力页、资料库、复习集、五日单元）保持不变。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import ko_pron
from daily_questions import build_daily_questions, vocabulary_display

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
[hidden]{display:none!important}
:root{--bg:#fbfaf7;--surface:#fff;--ink:#1d1c1a;--muted:#6b6862;--line:#e4e0d8;
--accent:#b4472e;--ok:#2e7d4f;--bad:#b3261e;--radius:14px;--max:760px}
@media (prefers-color-scheme:dark){:root{--bg:#171614;--surface:#201f1c;--ink:#efede7;
--muted:#a39e94;--line:#35322c;--accent:#e0704f;--ok:#6fbf8f;--bad:#f08a80}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.7 -apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP","PingFang SC",sans-serif}
a{color:var(--accent)}
.wrap{max-width:var(--max);margin:0 auto;padding:18px 14px 104px}
h1.lesson{font-size:17px;font-weight:650;margin:0 0 16px;color:var(--muted)}
h1.lesson b{color:var(--ink)}
section.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
padding:16px;margin:14px 0}
h2{font-size:16px;margin:0 0 10px;display:flex;align-items:center;gap:8px}
h2 .count{font-size:12px;color:var(--muted);font-weight:400}
.btn{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:10px;
padding:9px 14px;font-size:15px;cursor:pointer}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn:disabled{opacity:.45;cursor:not-allowed}
.small{font-size:12px;color:var(--muted)}
.review-link{display:inline-block;margin-bottom:8px;color:var(--accent)}
.mask-switch{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 12px}
.mask-switch button{font:inherit;font-size:12px;padding:5px 11px;border:1px solid var(--line);
border-radius:999px;background:var(--surface);color:var(--muted);cursor:pointer}
.mask-switch button[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.mask{filter:blur(6px);color:transparent;user-select:none;transition:filter .12s}
.mask.peek{filter:none;color:inherit}
.show-all{float:right;margin:0 0 6px 10px;font:inherit;font-size:11px;padding:3px 10px;
border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--muted);cursor:pointer}
.show-all:disabled{opacity:.75;cursor:default}
.item.co-show .mask,.gcard.co-show .mask{filter:none!important;color:inherit!important}
.item{border-top:1px dashed var(--line);padding:14px 0}
.item:first-of-type{border-top:0;padding-top:2px}
.jp{font-size:23px;font-weight:700;overflow-wrap:anywhere;line-height:1.4}
.vocab-pair{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,3fr);
column-gap:clamp(16px,5vw,48px);align-items:start;text-align:left}
.vocab-pair .zh{margin-top:0}
.vocab-example{margin-top:6px}
.vocab-example summary{display:list-item;width:fit-content;padding:4px 0}
.jp.small-jp{font-size:15px;font-weight:600}
.kana-line{font-size:12px;color:var(--muted);letter-spacing:.04em;margin-bottom:1px}
.ko-read{font-size:14px;color:var(--accent);margin-top:2px;letter-spacing:.02em;overflow-wrap:anywhere}
.ko-read .lb{font-size:10px;color:var(--muted);letter-spacing:0;margin-right:6px;vertical-align:1px}
.zh{font-size:16px;margin-top:2px;overflow-wrap:anywhere}
.ko{font-size:12.5px;color:var(--muted);margin-top:2px}
.ex{margin-top:8px;padding-left:10px;border-left:2px solid var(--line)}
.ex-ja{font-size:15px;overflow-wrap:anywhere}
.ex-ko{font-size:13px;color:var(--accent);overflow-wrap:anywhere;margin-bottom:1px}
.ex-zh{font-size:14px;color:var(--muted);margin-top:1px;overflow-wrap:anywhere}
.speak{border:0;background:none;color:var(--accent);font-size:12px;cursor:pointer;padding:2px 0}
ruby rt{font-size:.55em;color:var(--muted);font-weight:400}
.rates{display:flex;gap:6px;margin-top:6px}
.rates button{font:inherit;font-size:11px;padding:3px 9px;border:1px solid var(--line);
border-radius:999px;background:var(--surface);color:var(--muted);cursor:pointer}
.rates button[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.pattern{font-size:21px;font-weight:700;overflow-wrap:anywhere}
.grammar-transfer{margin:0 0 10px;padding:8px 12px;border-left:3px solid var(--accent);background:var(--bg);overflow-wrap:anywhere}
.grammar-transfer strong{display:block;font-size:1.13rem;line-height:1.5}
.grammar-transfer .small{margin-top:3px}
.conn{font-size:13px;color:var(--muted);overflow-wrap:anywhere}
.ko-box{background:var(--bg);border:1px solid var(--line);padding:8px 10px;margin:8px 0;font-size:13px}
.gcard{border-top:1px dashed var(--line);padding:14px 0}
.gcard:first-child{border-top:0;padding-top:0}
.listen-box{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:14px}
audio{width:100%;margin:6px 0}
.passage{white-space:pre-line;padding:12px;background:var(--bg);border-radius:8px;margin-bottom:10px}
.q{border-top:1px dashed var(--line);padding:14px 0}
.q:first-child{border-top:0;padding-top:2px}
.q .prompt{font-size:15px;white-space:pre-line;overflow-wrap:anywhere}
.q .opts{display:grid;gap:6px;margin-top:8px}
.opt{display:flex;gap:8px;align-items:flex-start;border:1px solid var(--line);border-radius:8px;
padding:8px;cursor:pointer;font-size:15px}
.opt input{margin-top:5px;flex:none}
.opt.correct{border-color:var(--ok);background:rgba(46,125,79,.08)}
.opt.wrong{border-color:var(--bad)}
.fb{font-size:13px;margin-top:6px}.fb.ok{color:var(--ok)}.fb.bad{color:var(--bad)}
.q-actions{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap}
.qscore{font-size:13px;color:var(--muted);margin-bottom:8px}
.foot{position:fixed;left:0;right:0;bottom:0;background:var(--surface);border-top:1px solid var(--line);
padding:10px 14px;display:flex;gap:10px;align-items:center;justify-content:center;z-index:30}
.foot .btn{flex:1;max-width:280px}
.foot .status{flex:1;max-width:320px;font-size:12px;color:var(--muted)}
details summary{cursor:pointer;color:var(--muted);font-size:13px}
.kstrip{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.kchip{font-size:13px;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:4px 8px}
.resource-link{display:block;padding:8px 0}.week-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px}
.home-start{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.home-start .btn{text-decoration:none}
.home-stage{margin-top:16px}
.home-stage h2{margin-bottom:4px}
.home-weeks details{border-top:1px solid var(--line);padding:8px 0}
.home-weeks summary{padding:4px 0;font-size:14px}
.home-lessons{list-style:none;padding:0;margin:8px 0;display:grid;grid-template-columns:repeat(auto-fit,minmax(78px,1fr));gap:6px}
.home-lessons a{display:block;text-align:center;padding:5px;border:1px solid var(--line);border-radius:8px;text-decoration:none}
.home-resources{display:flex;gap:8px 18px;flex-wrap:wrap}
.listen-box .q:last-of-type{padding-bottom:8px}
.lesson-nav{display:flex;justify-content:space-between;gap:16px;margin-top:28px;font-size:14px}
@media(min-width:1024px){.wrap{max-width:820px}.foot{position:static;background:none;border:0;margin-top:12px}}
@media(max-width:480px){.jp{font-size:21px}.q .opt{font-size:14px}}
button:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
@media print{.foot,.mask-switch,.rates,.speak,.btn,.show-all{display:none!important}.mask{filter:none!important;color:inherit!important}}
"""


JS = r"""
(function(){
'use strict';
var STORE='nh80.v11.', DAY=Number(document.body.dataset.day)||0;
function $(s,r){return (r||document).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))}
function fnv(t){var s=String(t==null?'':t).normalize('NFKC').replace(/\s+/g,'');
 var h=2166136261>>>0;for(const ch of s){h^=ch.codePointAt(0);h=Math.imul(h,16777619)>>>0}return h.toString(16)}
function reveal(el){el.classList.add('peek');setTimeout(function(){el.classList.remove('peek')},3000)}
function applyScope(sec,mode){
 if(!sec)return;
 if(PEEK){clearInterval(PEEK.timer);PEEK.box.classList.remove('co-show');
  PEEK.btn.disabled=false;PEEK.btn.textContent=PEEK.label;PEEK=null}
 $$('[data-role]',sec).forEach(function(el){
  var r=el.getAttribute('data-role');
  var hide=(mode==='both')||(mode==='zh'&&r==='zh')||(mode==='ja'&&r==='ja');
  el.classList.toggle('mask',hide);if(!hide)el.classList.remove('peek');
  if(hide){el.setAttribute('tabindex','0');el.setAttribute('aria-label','内容已遮盖，点击临时查看')}
  else{el.removeAttribute('tabindex');el.removeAttribute('aria-label')}
 });
 $$('.mask-switch button',sec).forEach(function(b){
  b.setAttribute('aria-pressed',String(b.getAttribute('data-mask')===mode))});
 $$('[data-show-all]',sec).forEach(function(b){b.hidden=(mode==='all')});
 try{localStorage.setItem(STORE+'mask.'+sec.id,mode)}catch(e){}
}
var PEEK=null;
function showAll(btn){
 var box=btn.closest('.item,.gcard');if(!box)return;
 if(PEEK){clearInterval(PEEK.timer);PEEK.btn.disabled=false;PEEK.btn.textContent=PEEK.label;PEEK.box.classList.remove('co-show')}
 var label=btn.textContent.trim()||'显示';
 box.classList.add('co-show');btn.disabled=true;
 var left=10;btn.textContent=left+'秒';
 var state={box:box,btn:btn,label:label,timer:null};
 state.timer=setInterval(function(){
  left--;btn.textContent=left+'秒';
  if(left<=0){clearInterval(state.timer);box.classList.remove('co-show');
   btn.disabled=false;btn.textContent=label;PEEK=null}
 },1000);
 PEEK=state;
}
var QUESTIONS=$$('.q'), RESULTS={}, RATINGS={}, RETRY=null, STARTED=Date.now();
var TRANSCRIPT=$('#listenTranscript'), SEEN_TRANSCRIPT=false;
if(TRANSCRIPT)TRANSCRIPT.addEventListener('toggle',function(){if(TRANSCRIPT.open)SEEN_TRANSCRIPT=true});
function saveLocal(){try{localStorage.setItem(STORE+'state.'+DAY,JSON.stringify({
 results:RESULTS,ratings:RATINGS,retry:RETRY}))}catch(e){}}
function restore(){
 try{
  var saved=JSON.parse(localStorage.getItem(STORE+'state.'+DAY)||'null');
  if(saved){
   RATINGS=saved.ratings||{};
   QUESTIONS.forEach(function(q){
    var id=q.dataset.qid, r=(saved.results||{})[id];
    if(r&&$$('.opt',q).some(function(opt){return $('span',opt).textContent===r.answer})){
     RESULTS[id]=Object.assign({},r,{correct:fnv(r.answer)===q.dataset.h});
    }
   });
   if(saved.retry&&Array.isArray(saved.retry.ids)&&saved.retry.ids.length&&
      saved.retry.ids.every(function(id){return RESULTS[id]&&!RESULTS[id].correct})){
    RETRY=saved.retry;
   }
  }
 }catch(e){}
 Object.keys(RATINGS).forEach(function(kid){$$('[data-rate][data-kid="'+kid+'"]').forEach(function(b){
  b.setAttribute('aria-pressed',String(b.getAttribute('data-rate')===RATINGS[kid]))})});
 renderQuestions();
}
function activeResults(){return RETRY?RETRY.results:RESULTS}
function wrongIds(){return Object.values(activeResults()).filter(function(r){return !r.correct})
 .map(function(r){return r.qid})}
function renderQuestion(q,r){
 q.toggleAttribute('data-done',!!r);
 $$('.opt',q).forEach(function(opt){
  var input=$('input',opt), selected=!!r&&$('span',opt).textContent===r.answer;
  input.disabled=!!r;
  input.checked=selected;
  opt.classList.toggle('correct',!!r&&opt.dataset.oh===q.dataset.h);
  opt.classList.toggle('wrong',selected&&!r.correct);
 });
 var fb=$('.fb',q);
 fb.hidden=!r;
 fb.classList.toggle('ok',!!r&&r.correct);
 fb.classList.toggle('bad',!!r&&!r.correct);
 fb.textContent=r?(r.correct?'答对了。':'答错了，正确项已标绿。'):'';
}
function renderQuestions(){
 var results=activeResults(), visible=0;
 QUESTIONS.forEach(function(q){
  q.hidden=!!RETRY&&!RETRY.ids.includes(q.dataset.qid);
  if(q.hidden)return;
  $('.q-number',q).textContent=++visible+'. ';
  renderQuestion(q,results[q.dataset.qid]);
 });
 var listening=$('#lessonListening');if(listening)listening.hidden=!!RETRY&&!$('.q:not([hidden])',listening);
 updateScore();
}
function updateScore(){
 var el=$('#qscore'), button=$('#retryWrong');
 if(!el||!button)return;
 var wrong=wrongIds().length, done=Object.keys(activeResults()).length;
 var total=RETRY?RETRY.ids.length:QUESTIONS.length;
 el.textContent=(RETRY?'错题重练 · ':'')+'已答 '+done+' / '+total+'　答对 '+(done-wrong)
  +(RETRY&&done===total&&!wrong?' · 本轮错题已全部答对':'');
 button.disabled=!wrong||(!!RETRY&&done<total);
 button.textContent=wrong?'错题重练（'+wrong+'）':'错题重练';
 $('#showAllQuestions').hidden=!RETRY;
}
function startRetry(){
 var ids=wrongIds();if(!ids.length)return;
 RETRY={ids:ids,results:{}};
 STARTED=Date.now();
 QUESTIONS.forEach(function(q){
  if(!ids.includes(q.dataset.qid))return;
  var options=$$('.opt',q);
  // Rotate by a random nonzero offset so the previous correct position always changes.
  var shift=1+Math.floor(Math.random()*(options.length-1));
  var list=$('.opts',q);
  options.slice(shift).concat(options.slice(0,shift)).forEach(function(opt){list.appendChild(opt)});
 });
 saveLocal();renderQuestions();$('#qscore').focus();
}
var retryButton=$('#retryWrong'), allQuestionsButton=$('#showAllQuestions');
if(retryButton)retryButton.addEventListener('click',startRetry);
if(allQuestionsButton)allQuestionsButton.addEventListener('click',function(){
 RETRY=null;saveLocal();renderQuestions();$('#qscore').focus();
});
document.addEventListener('change',function(e){
 var input=e.target, lab=input.closest('.q .opt');
 if(!lab||!input.checked)return;
 var q=lab.closest('.q');if(q.hasAttribute('data-done'))return;
 var answer=$('span',lab).textContent, id=q.dataset.qid;
 var result={qid:id,answer:answer,correct:fnv(answer)===q.dataset.h,
  hinted:id.startsWith('L-')&&(SEEN_TRANSCRIPT||!!TRANSCRIPT?.open),revealed:false,seconds:Math.min(86400,Math.round((Date.now()-STARTED)/1000))};
 activeResults()[id]=result;
 renderQuestion(q,result);saveLocal();updateScore();
 if(!RETRY)updateReviewLink();
});
function speak(text,btn){
 if(!window.speechSynthesis){if(btn)btn.textContent='此设备不支持朗读';return}
 var u=new SpeechSynthesisUtterance(text);u.lang='ja-JP';u.rate=.95;
 if(btn){var label=btn.textContent;u.onerror=function(){btn.textContent='朗读不可用'};
  u.onend=function(){btn.textContent=label}}
 window.speechSynthesis.cancel();window.speechSynthesis.speak(u);
}
document.addEventListener('click',function(e){
 var mb=e.target.closest('.mask-switch button');
 if(mb){applyScope(mb.closest('section'),mb.getAttribute('data-mask'));return}
 var sb=e.target.closest('[data-show-all]');
 if(sb){showAll(sb);return}
 var m=e.target.closest('.mask');if(m){reveal(m);return}
 var sp=e.target.closest('[data-speak]');
 if(sp){speak(sp.getAttribute('data-speak'),sp);return}
 var rt=e.target.closest('[data-rate]');
 if(rt){var kid=rt.getAttribute('data-kid'),v=rt.getAttribute('data-rate');RATINGS[kid]=v;
  $$('[data-rate][data-kid="'+kid+'"]').forEach(function(b){b.setAttribute('aria-pressed',String(b===rt))});
  saveLocal();return}
});
document.addEventListener('keydown',function(e){
 if((e.key==='Enter'||e.key===' ')&&e.target.classList&&e.target.classList.contains('mask')){
  e.preventDefault();reveal(e.target)}
});
['vocab','grammar'].forEach(function(id){var s=$('#'+id);if(!s)return;
 var saved='all';try{saved=localStorage.getItem(STORE+'mask.'+id)||'all'}catch(e){}
 if(['all','zh','ja','both'].indexOf(saved)<0)saved='all';
 applyScope(s,saved)});
restore();
function updateReviewLink(){
 var link=$('#dueReviewLink');
 if(!link||!window.NHReview)return;
 try{
  NHReview.lesson(DAY,RESULTS);
  var count=NHReview.due().length;
  link.textContent=count?'到期复习（'+count+'）':'到期复习';
 }catch(e){link.textContent='浏览器无法保存复习排期'}
}
updateReviewLink();
var f=$('#finish');
if(f)f.addEventListener('click',function(){
 var meta=window.__PAGE__||{},qs=Object.keys(RESULTS).map(function(k){return RESULTS[k]});
 if(!qs.length){$('#finishStatus').textContent='请先完成练习中的单选题。';return}
 var right=qs.filter(function(x){return x.correct}).length;
 var wrong=qs.filter(function(x){return !x.correct}).map(function(x){
  return {qid:x.qid,knowledge_ids:(meta.q_kids||{})[x.qid]||[]}});
 var payload={v:4,day:DAY,completed_at:new Date().toISOString(),
  required_ids:meta.required_ids||[],extra_ids:meta.extra_ids||[],grammar_ids:meta.grammar_ids||[],
  questions:qs,accuracy:qs.length?right/qs.length:0,self_rating:RATINGS,
  wrong_summary:wrong,
  review_summary:Object.keys(RATINGS).filter(function(k){return RATINGS[k]!=='good'}),
  note:''};
 f.disabled=true;f.textContent='正在保存…';
 var status=$('#finishStatus');if(status)status.textContent='';
 fetch('/api/progress',{method:'POST',headers:{'content-type':'application/json'},
  body:JSON.stringify(payload)}).then(function(r){return r.json().then(function(d){
   if(!r.ok||d.ok!==true)throw new Error(d.reason||('HTTP '+r.status));return d})})
  .then(function(){saveLocal();try{localStorage.setItem('nh80.completed.'+DAY,'1')}catch(e){}
   f.textContent='已完成';if(status)status.textContent='学习情况已保存，会话可读取。'})
  .catch(function(e){f.disabled=false;f.textContent='完成';
   if(status)status.textContent='云端暂不可用（'+e.message+'）；记录已留在本机。'});
});
})();
"""


# ---------------------------------------------------------------------------
# 外部资源页（沿用 v7 已核实清单，保持不变）
# ---------------------------------------------------------------------------
def resource_sources():
    p = ROOT / "knowledge/resources_v7.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"sources": json.loads((ROOT / "knowledge/resources.json").read_text(encoding="utf-8"))["resources"],
            "stage_plan": [], "conclusion": {}}


def is_rss(x):
    return any(k in (x.get("url") or "") for k in ("anchor.fm", "feeds.redcircle", "/rss"))


def real_listen_links(day):
    data = resource_sources()
    by_id = {x["id"]: x for x in data["sources"]}
    stage = next((x for x in data.get("stage_plan", [])
                  if x["days"].split("-")[0].isdigit()
                  and int(x["days"].split("-")[0]) <= day <= int(x["days"].split("-")[1])), None)
    ids = (stage or {}).get("items", [])
    allowed = [by_id[i] for i in ids if i in by_id and by_id[i].get("embed") == "link"
               and by_id[i].get("type") in ("listening", "video", "mock")
               and by_id[i].get("free") is not False]
    chosen = [x for x in allowed if not is_rss(x)][:3]
    for x in allowed:
        if len(chosen) >= 3:
            break
        if x not in chosen:
            chosen.append(x)
    return " · ".join('<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>'
                      % (esc(x["url"]), esc(x["title"][:18])) for x in chosen[:3])


def src_meta(x):
    bits = []
    if x.get("level"):
        bits.append("级别 " + str(x["level"]))
    if x.get("speed"):
        bits.append(str(x["speed"]))
    if x.get("transcript") is True:
        bits.append("有脚本")
    if x.get("free") is False:
        bits.append("付费")
    if x.get("region_limit"):
        bits.append("地区限制")
    if x.get("requires_login"):
        bits.append("需登录")
    return " · ".join(bits)


def link_card(x):
    note = "（RSS 订阅，用播客 App 打开）" if is_rss(x) else ""
    return ('<section class="card"><h2><a href="%s" target="_blank" rel="noopener noreferrer">%s</a>%s</h2>'
            '<p class="small">%s</p><p>%s</p><p class="small">许可：%s</p></section>'
            % (esc(x["url"]), esc(x["title"]), note, esc(src_meta(x)),
               esc(x.get("usage") or ""), esc(x.get("license") or "")))


def audio_card(x):
    srcs = ''
    if x.get("mp3_url"):
        srcs += '<source src="%s" type="audio/mpeg">' % esc(x["mp3_url"])
    srcs += '<source src="%s" type="audio/ogg">' % esc(x.get("embed_url") or "")
    fallback = ('<a href="%s" target="_blank" rel="noopener noreferrer">打开来源文件页收听</a>'
                % esc(x.get("file_url") or x["url"]))
    return ('<section class="card"><h2>%s</h2>'
            '<audio controls preload="none" aria-label="%s">%s%s</audio>'
            '<p class="small">%s　·　已提供 mp3 / Ogg 双格式官方转码；若浏览器不支持，请%s。</p>'
            '<p class="small">许可：%s　·　署名：%s　·　'
            '<a href="%s" target="_blank" rel="noopener noreferrer">文件页</a>　·　'
            '<a href="%s" target="_blank" rel="noopener noreferrer">许可全文</a></p></section>'
            % (esc(x["title"]), esc(x["title"]), srcs, fallback,
               esc(src_meta(x)), fallback, esc(x.get("license") or ""),
               esc(x.get("attribution") or "见文件页"),
               esc(x.get("file_url") or x["url"]), esc(x.get("license_url") or x["url"])))


# ---------------------------------------------------------------------------
# 读音标注（v12，2026-11-12 按用户要求重排）
#
# 新词区的顺序：平假读音 → 日语单词 → 韩语发音 → 中文 → 例句韩语读音 → 例句。
# 原则：同一条信息只出现一次。假名词不再加 ruby（单词本身就是假名）、
# 也不再单独来一行「假名」，那一行让给韩语发音；例句不再列「读音提示：词（词）」
# 这种把词重复两遍的行，改成整句韩语读音（能整句解析时）。
# 所有韩语元素带 data-role="zh"：遮中文时韩语一起遮，免得泄题。
# ---------------------------------------------------------------------------
def jp_word(surface, kana):
    """日语单词本体：假名词原样，汉字词…也原样（读音由上方 .kana-line 给出）。"""
    return esc(surface)


def kana_line(surface, kana):
    """平假读音行：只在读音和词形不同（即含汉字）时才输出，否则是重复。"""
    if not kana or kana == surface:
        return ""
    return '<div class="kana-line" data-role="ja">%s</div>' % esc(kana)


def pattern_ko(g, reader):
    """句型读音。

    优先用种子里的 `pattern_kana`（含汉字日语句型的读音：〜方＝〜かた、〜に比べて＝〜にくらべて）；
    没有就退回 pattern 本身。两种情况都用 ReadingIndex 解析——解析不了的汉字（「形容词」「普通形」
    这类中文元语言，或 〜の方が 里读 ほう 的 方）返回 None，这一行就**不出现**，不硬转写。
    """
    if not isinstance(g, dict) or not reader:
        return ""
    src = (g.get("pattern_kana") or g.get("pattern") or "").strip()
    src = re.sub(r"（[^）]*）|\([^)]*\)", "", src).strip()
    if not src:
        return ""
    kana = reader.reading(src)
    return ko_pron.to_hangul(kana) if kana else ""


def ko_read_line(text, label="발음"):
    """韩语发音行；text 已经是한글。伪造不出来就返回空串。"""
    if not text:
        return ""
    lb = '<span class="lb">%s</span>' % label if label else ""
    return '<div class="ko-read" data-role="zh" lang="ko">%s%s</div>' % (lb, esc(text))


def ruby_text(ja, mapping):
    """给日文原文里出现的当天汉字词加 <ruby>；假名词不加（加了就是重复）。"""
    text = str(ja or "")
    if not mapping:
        return esc(text)
    out, i, last = [], 0, 0
    while i < len(text):
        hit = next((kv for kv in mapping if text.startswith(kv[0], i)), None)
        if hit:
            out.append(esc(text[last:i]))
            out.append("<ruby>%s<rt>%s</rt></ruby>" % (esc(hit[0]), esc(hit[1])))
            i += len(hit[0])
            last = i
        else:
            i += 1
    out.append(esc(text[last:]))
    return "".join(out)


def example_html(ex, mapping, ko=""):
    """例句：韩语读音 → 日语（含当天词的 ruby）→ 中文。"""
    if not ex or not ex.get("ja"):
        return ""
    ja = ex.get("ja", "")
    ko_html = ('<div class="ex-ko" data-role="zh" lang="ko">%s</div>' % esc(ko)) if ko else ""
    return ('<div class="ex">%s'
            '<div class="ex-ja" data-role="ja">%s</div>'
            '<div class="ex-zh" data-role="zh">%s</div>'
            '</div>' % (ko_html, ruby_text(ja, mapping), esc(ex.get("zh") or ex.get("en") or "")))


def kana_map(day, vocab):
    """当天汉字词形 → 假名，用于例句里的 <ruby> 注音（假名词不进表，避免自己注自己）。"""
    out = {}
    for vid in day["new_vocab_ids"]:
        v = vocab[vid]
        surface = v.get("surface") or ""
        kana = v.get("kana") or ""
        if surface and kana and surface != kana and len(surface) >= 2:
            out[surface] = kana
    return sorted(out.items(), key=lambda kv: -len(kv[0]))


def rates_html(kid):
    return ('<div class="rates">' + "".join(
        '<button type="button" data-kid="%s" data-rate="%s" aria-pressed="false">%s</button>'
        % (esc(kid), code, label)
        for code, label in (("again", "忘了"), ("hard", "不熟"), ("good", "记得"))) + "</div>")


def build_review_html(day, vocab, grammar, kanji, reader):
    """今日复习：平假 → 单词 → 韩语发音 → 中文 → 自评，和当天新词一个版式。"""
    rows = []
    for kid in day.get("review_knowledge_ids") or []:
        if kid in vocab:
            v = vocab[kid]
            kana = v.get("kana", "")
            rows.append((kid, v["surface"], kana_line(v["surface"], kana),
                         ko_read_line(ko_pron.pron(kana)), v["meaning_zh"]))
        elif kid in grammar:
            g = grammar[kid]
            rows.append((kid, g["pattern"], "",
                         ko_read_line(pattern_ko(g, reader)), g["meaning_zh"]))
        elif kid in kanji:
            k = kanji[kid]
            reading = "、".join((k.get("onyomi") or []) + (k.get("kunyomi") or []))[:24]
            rows.append((kid, k["char"],
                         '<div class="kana-line" data-role="ja">%s</div>' % esc(reading) if reading else "",
                         ko_read_line(kanji_ko_read(k)), k["meaning_zh"]))
    if not rows:
        return '<p class="small">今天没有安排旧内容，直接看新词。</p>'
    return "".join(
        '<div class="item">%s<div class="jp" data-role="ja">%s</div>%s'
        '<div class="zh" data-role="zh">%s</div>%s</div>'
        % (kana_html, esc(jp), ko_html, esc(zh), rates_html(kid))
        for kid, jp, kana_html, ko_html, zh in rows)


def kanji_ko_read(item):
    """汉字条目：音读/训读的韩语读音（예: ジン、ニン → 진·닌）."""
    parts = []
    for field in ("onyomi", "kunyomi"):
        values = [ko_pron.pron(str(x).replace(".", "").replace("-", ""))
                  for x in (item.get(field) or [])[:3]]
        values = [x for x in values if x]
        if values:
            parts.append("·".join(values))
    return " / ".join(parts)


def build_vocab_html(day, vocab, kanji, reader):
    mapping = kana_map(day, vocab)
    core = set(day.get("core_vocab_ids") or [])
    out = []
    for vid in day["new_vocab_ids"]:
        v = vocab[vid]
        surface, kana = v["surface"], v.get("kana") or ""
        meaning, readings = vocabulary_display(v)
        ex = (v.get("examples") or [{}])[0]
        ko = v.get("ko_hint") or v.get("ko_hanja") or ""
        tag = "" if vid in core else '<span class="small"> · 选学</span>'
        out.append(
            '<div class="item">'
            '<div class="vocab-pair"><div lang="ja">%s<div class="jp" data-role="ja">%s</div></div>'
            '<div><div class="zh" data-role="zh">%s%s</div>%s</div></div>'
            '<button class="show-all" type="button" data-show-all aria-label="临时显示三种语言 10 秒" hidden>显示</button>'
            '%s%s</div>'
            % (kana_line(surface, "／".join(readings)), jp_word(surface, kana),
               esc(meaning), tag, ko_read_line(ko_pron.pron("／".join(readings))),
               ('<details class="vocab-example"><summary>例句</summary>%s%s</details>'
                % (('<div class="ko" data-role="zh">韩语参考：%s</div>' % esc(ko)) if ko else "",
                   example_html(ex, mapping, reader.hangul(ex.get("ja", ""))))) if ex.get("ja") else "",
               rates_html(vid)))
    character_rows = []
    for kid in day["new_kanji_ids"]:
        item = kanji[kid]
        readings = []
        for field, label in (("onyomi", "音读"), ("kunyomi", "训读")):
            values = item.get(field) or []
            if values:
                readings.append(label + " " + "、".join(values[:3]))
        ko_read = kanji_ko_read(item)
        rows = ('<div class="small" data-role="ja">%s</div>' % esc(" · ".join(readings))) if readings else ""
        if ko_read:
            rows += '<div class="small ko-read" data-role="zh" lang="ko">%s</div>' % esc(ko_read)
        if item.get("ko_hanja"):
            rows += '<div class="small" data-role="zh">韩语字音 %s</div>' % esc(item["ko_hanja"])
        character_rows.append('<li><strong lang="ja">%s</strong> <span data-role="zh">%s</span>%s</li>'
                              % (esc(item["char"]), esc(item["meaning_zh"]), rows))
    if character_rows:
        out.append('<details><summary>今日汉字 · %d 个</summary><ul>%s</ul></details>'
                   % (len(character_rows), "".join(character_rows)))
    return "".join(out)


def build_grammar_html(day, grammar, reader):
    out = []
    for gid in day["new_grammar_ids"]:
        g = grammar[gid]
        pattern = g["pattern"]
        exs = "".join(example_html(e, [], reader.hangul(e.get("ja", "")))
                      for e in (g.get("examples") or [])[:3])
        err = (g.get("common_errors") or [{}])[0]
        ko = ('<div class="grammar-transfer ko-box" data-role="zh">'
              '<span class="small">韩语对应</span><strong lang="ko">%s</strong>%s</div>'
              % (esc(g["ko_equiv"]), '<div class="small">%s</div>' % esc(g["ko_diff"]) if g.get("ko_diff") else "")
              ) if g.get("ko_equiv") else ""
        usage = ('<div class="small" data-role="zh">%s</div>' % esc(g.get("usage", ""))) if g.get("usage") else ""
        trap = ('<details><summary>易错点</summary><p class="small">'
                '<span data-role="ja">%s → %s</span>'
                '<span data-role="zh">（%s）</span></p></details>'
                % (esc(err.get("wrong")), esc(err.get("fix")), esc(err.get("why")))) if err.get("wrong") else ""
        out.append(
            '<div class="gcard">'
            '<button class="show-all" type="button" data-show-all aria-label="临时显示三种语言 10 秒" hidden>显示</button>'
            '%s<div class="pattern" data-role="ja">%s</div>'
            '%s'
            '<div class="zh" data-role="zh">%s</div>'
            '<div class="conn" data-role="ja">%s</div>'
            '%s%s%s%s</div>'
            % (ko, esc(pattern), ko_read_line(pattern_ko(g, reader)),
               esc(g["meaning_zh"]), esc(g.get("connection", "")),
               usage, exs, trap, rates_html(gid)))
    return "".join(out) or '<p class="small">今天没有新语法。</p>'


# ---------------------------------------------------------------------------
# 一整块练习：以必做骨架为准，按知识点去重，补齐当天全部新词 + 新语法
# ---------------------------------------------------------------------------
def build_questions_html(questions, start=1):
    rows = []
    for i, q in enumerate(questions, start):
        passage = ('<div class="passage" lang="ja">%s</div>' % esc(q["passage"])) if q.get("passage") else ""
        opts = "".join(
            '<label class="opt" data-oh="%s"><input type="radio" name="q%d"><span>%s</span></label>'
            % (esc(q["oh"][j]), i, esc(o)) for j, o in enumerate(q["options"]))
        rows.append('<div class="q" data-qid="%s" data-h="%s">%s<div class="prompt" id="prompt-%d"><span class="q-number">%d. </span>%s</div>'
                    '<div class="opts" role="group" aria-labelledby="prompt-%d">%s</div>'
                    '<div class="fb" role="status" hidden></div></div>'
                    % (esc(q["qid"]), esc(q["h"]), passage, i, i, esc(q["prompt"]), i, opts))
    return "".join(rows)


def mask_switch(scope):
    return ('<div class="mask-switch" aria-label="%s遮盖">'
            '<button type="button" data-mask="all">显示</button>'
            '<button type="button" data-mask="zh">遮中文</button>'
            '<button type="button" data-mask="ja">遮日语</button>'
            '<button type="button" data-mask="both">双向</button></div>' % scope)


def day_page(d, review_html, vocab_html, grammar_html, questions_html, page_meta, listening_html):
    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<meta name="color-scheme" content="light dark">'
            '<title>Day %03d · %s | Nihongo 150</title>'
            '<link rel="icon" href="data:,"><link rel="stylesheet" href="assets/app.css"></head>'
            '<body data-day="%03d"><div class="wrap"><main>'
            '<h1 class="lesson">Day <b>%03d</b> · %s</h1>'
            '<section class="card" id="review"><h2>记忆曲线复习</h2>'
            '<a id="dueReviewLink" class="small review-link" href="review.html">到期复习</a>%s</section>'
            '<section class="card" id="vocab"><h2>今日新词 <span class="count">%d 个</span></h2>%s%s</section>'
            '<section class="card" id="grammar"><h2>今日语法 <span class="count">%d 条</span></h2>%s%s</section>'
            '<section class="card" id="questions"><h2>练习 <span class="count">%d 题</span></h2>'
            '<div class="qscore" id="qscore" role="status" tabindex="-1"></div>%s%s'
            '<div class="q-actions"><button class="btn" id="retryWrong" type="button" disabled>错题重练</button>'
            '<button class="btn" id="showAllQuestions" type="button" hidden>返回全部练习</button></div></section>'
            '<div class="foot"><button class="btn primary" id="finish" type="button">完成</button>'
            '<span class="status" id="finishStatus" role="status" aria-live="polite"></span></div>'
            '</main></div>'
            '<script>window.__PAGE__=%s;</script><script src="assets/review_schedule.js"></script><script src="assets/app.js"></script>'
            '</body></html>'
            % (d["day"], esc(d["theme"]), d["day"], d["day"], esc(d["theme"]),
               ('<details><summary>回看往日词句与汉字</summary>%s</details>' % review_html) if d.get("review_knowledge_ids") else "", len(d["new_vocab_ids"]), mask_switch("新词"), vocab_html,
               len(d["new_grammar_ids"]), mask_switch("语法"), grammar_html,
               page_meta["total"], questions_html, listening_html,
               json.dumps(page_meta, ensure_ascii=False)))


# ---------------------------------------------------------------------------
# 其它页面壳（复习集 / 五日单元）沿用共享 study.js
# ---------------------------------------------------------------------------
def study_page(title, body, day=0, unit=None):
    import study_ui
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="color-scheme" content="light dark"><title>' + esc(title) +
            ' · Nihongo 150</title><link rel="stylesheet" href="assets/app.css"></head>'
            '<body data-day="' + str(day) + '"><div class="wrap" style="max-width:920px"><main>'
            '<h1>' + esc(title) + '</h1>' + body + '</main></div>'
            '<script>window.__UNIT__=' + json.dumps(unit, ensure_ascii=False) +
            ';window.__PRACTICE__=' + json.dumps(unit["questions"] if unit else [], ensure_ascii=False) +
            '</script><script src="assets/review_schedule.js"></script><script src="assets/study.js"></script></body></html>')


def main(daily_by_day=None):
    import study_ui
    from quiz_v5 import public_question, day_questions, listening_quiz
    from practice_v9 import build_daily, build_unit
    from sentence_choices import build_for_day as sentence_questions

    cur = json.loads((ROOT / "curriculum/curriculum.json").read_text(encoding="utf-8"))
    vocab = {x["id"]: x for x in read("vocabulary.jsonl")}
    grammar = {x["id"]: x for x in read("grammar.jsonl")}
    kanji = {x["id"]: x for x in read("kanji.jsonl")}
    materials = {x["id"]: x for x in read("materials.jsonl")}
    sentence_rows = read("sentences.jsonl")
    supplement_path = ROOT / "knowledge/ko_reading_supplement.json"
    supplement = (json.loads(supplement_path.read_text(encoding="utf-8")).get("entries", [])
                  if supplement_path.exists() else [])
    reader = ko_pron.ReadingIndex(vocab.values(), supplement)
    audio_manifest_path = OUT / "audio/manifest.json"
    audio_manifest = json.loads(audio_manifest_path.read_text()) if audio_manifest_path.exists() else {"items": {}}

    if not OUT.is_dir():
        OUT.mkdir(parents=True)
    if not DATA.is_dir():
        DATA.mkdir(parents=True)
    if not (OUT / "assets").is_dir():
        (OUT / "assets").mkdir(parents=True)
    (DATA / "answer-key.json").unlink(missing_ok=True)
    for directory, pattern in ((OUT, "day-???.html"), (OUT, "unit-???.html"), (DATA, "day-???.json")):
        for path in directory.glob(pattern):
            suffix = path.stem[4:] if path.stem.startswith("day-") else path.stem[5:]
            if suffix.isdigit() and int(suffix) > len(cur["days"]):
                path.unlink()
    (OUT / "404.html").write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1"><title>页面未找到</title>'
        '<h1>页面未找到</h1><a href="/">返回课程目录</a></html>', encoding="utf-8")
    (OUT / "assets/app.css").write_text(CSS + study_ui.CSS, encoding="utf-8")
    (OUT / "assets/app.js").write_text(JS, encoding="utf-8")
    (OUT / "assets/study.js").write_text(study_ui.JS, encoding="utf-8")
    schedule_js = (ROOT / "scripts/review_schedule.js").read_text(encoding="utf-8")
    (OUT / "assets/review_schedule.js").write_text(schedule_js, encoding="utf-8")

    if daily_by_day is None:
        daily_by_day = {d["day"]: build_daily_questions(d, vocab, grammar) for d in cur["days"]}
    review_questions = {}
    for questions in daily_by_day.values():
        for q in questions:
            review_questions.setdefault(q["knowledge_ids"][0], []).append(q)

    catalog = []
    for day in cur["days"]:
        for kid in day["new_vocab_ids"]:
            v = vocab[kid]
            meaning, readings = vocabulary_display(v)
            catalog.append({"kid": kid, "front": v["surface"], "back": meaning,
                            "kana": "／".join(readings), "kind": "vocab", "day": day["day"]})
        for kid in day["new_grammar_ids"]:
            g = grammar[kid]
            catalog.append({"kid": kid, "front": g["pattern"], "back": g["meaning_zh"],
                            "kana": g.get("connection", ""), "example": g["examples"][0]["ja"], "kind": "grammar", "day": day["day"]})
        for kid in day["new_kanji_ids"]:
            k = kanji[kid]
            catalog.append({"kid": kid, "front": k["char"], "back": k["meaning_zh"],
                            "kana": "、".join(k.get("onyomi", [])), "kind": "kanji", "day": day["day"]})
    for entry in catalog:
        entry["review_questions"] = review_questions.get(entry["kid"], [])
    (DATA / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")

    (OUT / "review.html").write_text(study_page(
        "错题与复习集",
        '<p><a href="/">课程目录</a></p>'
        '<section class="card" id="scheduledReview"><h2>到期复习</h2><p class="small">正在加载词表…</p></section>'
        '<section class="card"><h2>回看错题与自评</h2><div id="personalReview"></div></section>' ), encoding="utf-8")
    for end in range(5, len(cur["days"]) + 1, 5):
        unit = build_unit(end, cur["days"], vocab, grammar, kanji)
        unit["items"] = [{k: v for k, v in x.items() if k != "review_questions"} for x in catalog if end - 4 <= x["day"] <= end and x["kind"] != "kanji"]
        unit["questions"] = [public_question(q) for q in unit["questions"]]
        body = ('<p class="small">五天学过的词汇与语法完整清单。</p>'
                '<div id="unitList"></div><section class="card"><h2>五日巩固 · 20 题</h2>'
                '<div id="practiceDeck"></div></section>')
        (OUT / ("unit-%03d.html" % end)).write_text(
            study_page("Day %d–%d · 五日复习" % (end - 4, end), body, end, unit), encoding="utf-8")

    totals = []
    lesson_revision = hashlib.sha256()
    for d in cur["days"]:
        n = d["day"]
        merged = daily_by_day[n]
        totals.append(len(merged))
        practice = [public_question(q) for q in build_daily(d, vocab, grammar, kanji)]
        sentences = [dict(public_question(q), direction=q["direction"], optional=q["optional"],
                          source_id=q["source_id"]) for q in sentence_questions(d, sentence_rows)]
        qs = [public_question(q) for q in day_questions(d, vocab, grammar, kanji, materials)
              if not q["qid"].startswith("L-")]
        vcards = []
        for vid in d["new_vocab_ids"]:
            v = vocab[vid]
            ex = (v.get("examples") or [{}])[0]
            vcards.append({"id": vid, "surface": v["surface"], "kana": v["kana"],
                           "meaning": v["meaning_zh"], "ko": v.get("ko_hint") or v.get("ko_hanja") or "",
                           "ko_pron": ko_pron.pron(v.get("kana") or ""),
                           "ko_status": v.get("ko_status"), "optional": vid in d.get("extension_vocab_ids", []),
                           "pos": v.get("pos", ""),
                           "ex": {"ja": ex.get("ja", ""), "zh": ex.get("zh", ""),
                                  "ko_pron": reader.hangul(ex.get("ja", ""))} if ex.get("ja") else None,
                           "audio": None})
        review = []
        for kid in d.get("review_knowledge_ids") or []:
            if kid in vocab:
                review.append({"kid": kid, "front": vocab[kid]["surface"],
                               "back": vocab[kid]["meaning_zh"], "kana": vocab[kid].get("kana", ""),
                               "ko_pron": ko_pron.pron(vocab[kid].get("kana") or "")})
            elif kid in grammar:
                review.append({"kid": kid, "front": grammar[kid]["pattern"],
                               "back": grammar[kid]["meaning_zh"], "kana": "",
                               "ko_pron": pattern_ko(grammar[kid], reader)})
            elif kid in kanji:
                k = kanji[kid]
                review.append({"kid": kid, "front": k["char"], "back": k["meaning_zh"],
                               "kana": "、".join((k.get("onyomi") or []) + (k.get("kunyomi") or [])),
                               "ko_pron": kanji_ko_read(k)})

        listening = None
        listening_html = ""
        audio_questions = []
        if d["material_ids"]:
            material = materials[d["material_ids"][0]]
            audio_questions = [public_question(q) for q in listening_quiz(d, material)]
            audio = audio_manifest.get("items", {}).get(material["id"])
            player = ('<audio controls preload="none" src="%s"></audio>' % esc(audio["url"]) if audio else
                      '<button class="btn" type="button" data-speak="%s">播放日语合成朗读</button>' % esc(material["audio_text"]))
            listening = {"id": material["id"], "title": material["title"], "questions": audio_questions}
            listening_html = ('<div class="listen-box" id="lessonListening"><h3>听力 · %s</h3>'
                              '<p class="small">先听一遍再答题。答后核对原文，找出漏听的条件和转折。</p>%s%s'
                              '<details id="listenTranscript"><summary>核对原文</summary><p lang="ja">%s</p></details></div>'
                              % (esc(material["title"]), player, build_questions_html(audio_questions, len(merged)+1),
                                 esc(material["text_ja"])))
        if d.get("practice_note"):
            listening_html += '<p>%s <a href="n2.html#official">打开 N2 官方练习</a></p>' % esc(d["practice_note"])
        lesson_questions = merged + audio_questions
        page_meta = {
            "day": n,
            "required_ids": d.get("core_vocab_ids") or [],
            "extra_ids": d.get("extension_vocab_ids") or [],
            "grammar_ids": d.get("new_grammar_ids") or [],
            "q_kids": {q["qid"]: q.get("knowledge_ids") or [] for q in lesson_questions},
            "total": len(lesson_questions),
        }
        page = day_page(d, build_review_html(d, vocab, grammar, kanji, reader),
                        build_vocab_html(d, vocab, kanji, reader), build_grammar_html(d, grammar, reader),
                        build_questions_html(merged), page_meta, listening_html)
        (OUT / ("day-%03d.html" % n)).write_text(page, encoding="utf-8")
        lesson_revision.update(page.encode())
        (DATA / ("day-%03d.json" % n)).write_text(json.dumps({
            "day": n, "phase": d["phase"], "theme": d["theme"], "can_do": d["can_do"],
            "minutes": d["minutes"], "blocks": d["blocks"], "listening": bool(d.get("listening")),
            "review": review, "vocab": vcards,
            "core_vocab_ids": d.get("core_vocab_ids"), "extension_vocab_ids": d.get("extension_vocab_ids"),
            "grammar": [dict(grammar[g], ko_pron=pattern_ko(grammar[g], reader))
                        for g in d["new_grammar_ids"]],
            "unit_questions": [public_question(q) for q in build_unit(n, cur["days"], vocab, grammar, kanji)["questions"]]
            if n % 5 == 0 else [],
            "practice": practice, "sentences": sentences, "quiz": qs,
            "questions": merged, "listening_material": listening,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    (OUT / "n3-mock.html").write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1"><title>N3 自测入口</title><h1>N3 自测</h1>'
        '<p>使用官方样题，答后对照答案。本站阶段练习不换算官方分数。</p>'
        '<a href="resources.html">打开官方听力、阅读与样题</a></html>', encoding="utf-8")
    (OUT / "manifest.webmanifest").write_text(json.dumps({
        "name": "Nihongo 150", "short_name": "Nihongo", "start_url": "/", "display": "standalone",
        "background_color": "#fbfaf7", "theme_color": "#b4472e",
        "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"}]},
        ensure_ascii=False), encoding="utf-8")

    n2_body = ('<p><a href="/">课程目录</a> · <a href="review.html">到期复习</a></p>'
               '<p>先复习到期词，学新词时先认日语读音。语法用韩语提示选日语句型，重点看助词、接续和语体。</p>'
               '<h2>Day 091–108 · 词汇与句型</h2><p>每天 25 个词。把容易望文生义的汉字词和不同读音放进错题复习。</p>'
               '<h2>Day 109–132 · 场景听解</h2><p>先听一次抓人物、条件和行动，再答题。答完打开原文找漏听的转折与否定。</p>'
               '<h2>Day 133–150 · 综合与模考</h2><p>从 Day 139 起每天 20 词。按官方卷做语言知识、阅读和听力，复盘两套题的时间和错因。</p>'
               '<h2 id="official">官方题型与原声</h2><ul>'
               '<li><a href="https://www.jlpt.jp/e/samples/forlearners.html">JLPT 官方样题</a> · 先熟悉题型</li>'
               '<li><a href="https://www.jlpt.jp/e/samples/sampleindex.html">JLPT 官方练习册两册</a> · N2 语言知识与阅读 105 分钟，听力 50 分钟</li>'
               '<li><a href="https://www.jlpt.jp/e/guideline/pdf/n2_e.pdf">N2 各题型说明</a></li></ul>'
               '<p class="small">每日原创听力由设备日语语音合成。正式计时使用官方原声。</p>'
               '<h2>60 天课程</h2><ul class="week-grid">'
               + "".join('<li><a href="day-%03d.html">Day %03d</a></li>' % (d, d) for d in range(91,151))
               + '</ul>')
    (OUT / "n2.html").write_text(study_page("N2 冲刺", n2_body), encoding="utf-8")

    optional_rows = []
    for kid in cur["optional_vocab_ids"]:
        word = vocab[kid]
        meaning, readings = vocabulary_display(word)
        optional_rows.append('<li><span lang="ja">%s（%s）</span> · %s</li>'
                             % (esc(word["surface"]), esc("／".join(readings)), esc(meaning)))
    (OUT / "optional-vocab.html").write_text(study_page(
        "选学词库", '<p><a href="/">课程目录</a></p><ul>' + "".join(optional_rows) + '</ul>'),
        encoding="utf-8")

    links = ('<nav class="home-start" aria-label="学习入口">'
             '<a id="resume" class="btn primary" href="day-001.html">开始 Day 001</a>'
             '<a class="btn" href="review.html">到期复习与错题</a></nav>')
    for label, start, end in (("N3 基础", 1, 90), ("N2 冲刺", 91, 150)):
        weeks = []
        for first in range(start, end + 1, 7):
            last = min(first + 6, end)
            days = "".join('<li><a href="day-%03d.html">Day %03d</a></li>' % (n, n)
                           for n in range(first, last + 1))
            weeks.append('<details data-start="%d" data-end="%d"><summary>Day %03d–%03d</summary>'
                         '<ul class="home-lessons">%s</ul></details>' % (first,last,first,last,days))
        guide = '<p><a href="n2.html">冲刺安排与官方练习</a></p>' if start == 91 else ""
        links += ('<section class="card home-stage"><h2>%s</h2>%s<div class="home-weeks">%s</div></section>'
                  % (label, guide, "".join(weeks)))
    links += ('<section class="card"><h2>学习资源</h2><nav class="home-resources" aria-label="学习资源">'
              '<a href="optional-vocab.html">选学词库</a><a href="resources.html">N3 官方练习</a>'
              '<a href="library.html">听读资料</a></nav>'
              '<details><summary>五日复习单元</summary><ul class="home-lessons">'
              + "".join('<li><a href="unit-%03d.html">%03d–%03d</a></li>' % (n,n-4,n)
                        for n in range(5, len(cur["days"]) + 1, 5)) + '</ul></details></section>')
    (OUT / "index.html").write_text(
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Nihongo 150</title><link rel="stylesheet" href="assets/app.css"></head>'
        '<body><div class="wrap"><main><h1>Nihongo 150</h1>'
        '<p class="small">词汇与读音 · 韩日语法对照 · 后段听解</p>'
        + links + '</main></div><script>'
        'try{var old=Number(localStorage.getItem("nh80.v16.lastDay")||localStorage.getItem("nh80.v15.lastDay")||localStorage.getItem("nh80.v11.lastDay")||0);'
        'var n=Number.isInteger(old)&&old>=0&&old<=150?Math.min(old+1,150):1;'
        'while(n<150&&localStorage.getItem("nh80.completed."+n)==="1")n++;'
        'var day=String(n).padStart(3,"0"),resume=document.getElementById("resume");'
        'resume.href="day-"+day+".html";resume.textContent=(n===1?"开始 Day ":"继续 Day ")+day;'
        'document.querySelectorAll(".home-weeks details").forEach(function(group){'
        'group.open=n>=Number(group.dataset.start)&&n<=Number(group.dataset.end)});'
        '}catch(e){}</script></body></html>', encoding="utf-8")


    rdata = resource_sources()
    sources = rdata["sources"]
    inline = [x for x in sources if x.get("embed") == "inline"]
    links2 = [x for x in sources if x.get("embed") == "link" and x.get("free") is not False]
    rejected = [x for x in sources if x.get("embed") == "none"]
    honesty = ('<p class="small"><strong>使用边界：</strong>独立听力资源包含 45 篇原创文本的合成语音（见 '
               '<a href="audio/NOTICE.txt">音频署名</a>）。下面这些真人材料<strong>不托管在本站</strong>：'
               '除明确开放许可、可在本页直接播放的 Commons 音频外，其余一律跳转到官方原站收听，'
               '不复制、不下载、不热链第三方音频。免费不等于可以任意转载。</p>')
    lhtml = ('<h1>真人听力 · 免费资源</h1>' + honesty +
             '<p><a href="/">返回课程</a> · <a href="resources.html">全部 N3 资源</a></p>'
             '<h2>可在本页播放（开放许可）</h2>' + "".join(audio_card(x) for x in inline))
    for st in rdata.get("stage_plan", []):
        lhtml += '<h2>Day %s · 建议组合</h2><p class="small">%s</p>' % (
            esc(st.get("days", "")), esc(st.get("note") or ""))
        for sid in st.get("items", []):
            x = next((y for y in sources if y["id"] == sid), None)
            if not x or x.get("embed") == "none":
                continue
            tag = "本页可播" if x.get("embed") == "inline" else "跳转原站"
            lhtml += ('<section class="card"><h2><a href="%s" target="_blank" rel="noopener noreferrer">%s</a>'
                      ' <span class="small">［%s］</span></h2><p class="small">%s</p><p>%s</p></section>'
                      % (esc(x["url"]), esc(x["title"]), tag, esc(src_meta(x)),
                         esc(x.get("usage") or "")))
    lhtml += ('<details><summary>未采用的源与原因（%d）</summary><ul>' % len(rejected)
              + "".join('<li><a href="%s" target="_blank" rel="noopener noreferrer">%s</a> — %s</li>'
                        % (esc(x["url"]), esc(x["title"]),
                           esc((x.get("risk") or x.get("license") or "许可待核实")[:160]))
                        for x in rejected) + '</ul></details>')
    (OUT / "listening.html").write_text(
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>真人听力 · Nihongo 150</title><link rel="stylesheet" href="assets/app.css"></head>'
        '<body><div class="wrap" style="max-width:760px">' + lhtml + '</div></body></html>',
        encoding="utf-8")

    rhtml = ('<h1>N3 学习资源</h1>' + honesty +
             '<p><a href="review.html">错题与个人复习集</a> · '
             '<a href="listening.html">真人听力与可播放的开放音频</a> · '
             '<a href="audio/NOTICE.txt">完整音频署名与许可声明</a></p>'
             '<h2>官方样题与免费真人听力（跳转原站）</h2>'
             + "".join(link_card(x) for x in links2)
             + '<details><summary>未采用：付费 / 地区限制 / 许可不明（%d）</summary><ul>' % len(rejected)
             + "".join('<li><a href="%s" target="_blank" rel="noopener noreferrer">%s</a> — %s</li>'
                       % (esc(x["url"]), esc(x["title"]),
                          esc((x.get("risk") or x.get("license") or "许可待核实")[:160]))
                       for x in rejected) + '</ul></details>'
             + '<h2>本地内容与署名</h2><p class="small">词汇等资源来自 OpenJLPT（CC BY-SA 4.0）；'
               '韩语词典字段来自韩国国立国语院 한국어기초사전（CC BY-SA 2.0 KR）；'
               '汉字韩语字音补充来自 KANJIDIC2（CC BY-SA 4.0）与 Unicode Unihan。'
               '原创文本合成音频：Kokoro-82M（Apache-2.0）+ UniDic 3.1.0。</p>')
    (OUT / "resources.html").write_text(
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>N3 学习资源</title><link rel="stylesheet" href="assets/app.css"></head>'
        '<body><div class="wrap" style="max-width:760px"><a href="/">返回课程</a>'
        + rhtml + '</div></body></html>', encoding="utf-8")

    library = '<h1>原创听读资料</h1><p class="small">按级别选一篇。先理解大意，再看译文。</p>'
    for level in ("N5", "N4", "N3", "N2"):
        library += '<h2>' + level + '</h2>'
        for m in materials.values():
            if m.get("level") != level or m.get("license") != "original" or not m.get("text_ja"):
                continue
            a = audio_manifest.get("items", {}).get(m["id"])
            audio_html = ('<audio controls preload="none" src="%s" aria-label="%s"></audio>'
                          '<p class="small">合成语音 · %s 秒</p>'
                          % (esc(a["url"]), esc(m["title"]), round(a["duration_sec"], 1))) if a else ''
            library += ('<details><summary>%s · %s</summary>%s<p lang="ja" class="passage">%s</p>'
                        '<button class="btn" data-speak="%s">设备朗读</button>'
                        '<details><summary>中文参考</summary><p>%s</p></details></details>'
                        % (esc(m["id"]), esc(m["title"]), audio_html, esc(m["text_ja"]),
                           esc(m["audio_text"]),
                           esc(m.get("text_zh") or "请先独立理解，再交会话答疑。")))
    (OUT / "library.html").write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1"><title>原创听读资料</title>'
        '<link rel="stylesheet" href="assets/app.css"><div class="wrap" style="max-width:760px">'
        '<a href="resources.html">返回官方资源</a>' + library + '</div>'
        '<script src="assets/app.js"></script></html>', encoding="utf-8")

    # HTML 模板必须进 revision，否则只改模板时 SW 不更新，用户会一直看到旧页面。
    revision = hashlib.sha256((CSS + JS + study_ui.CSS + study_ui.JS + schedule_js
                               + lesson_revision.hexdigest() + json.dumps(cur, ensure_ascii=False)).encode()).hexdigest()[:12]
    (OUT / "sw.js").write_text(
        "const C='nh80-v17-" + revision + "';self.addEventListener('install',e=>self.skipWaiting());"
        "self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(ks=>Promise.all("
        "ks.filter(k=>k!==C).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));"
        "self.addEventListener('fetch',e=>{if(e.request.method!=='GET'||new URL(e.request.url).origin!==location.origin||new URL(e.request.url).pathname.startsWith('/api/'))return;"
        "e.respondWith(fetch(e.request).then(r=>{if(r.ok){const c=r.clone();e.waitUntil(caches.open(C).then(x=>x.put(e.request,c)))}return r})"
        ".catch(()=>caches.match(e.request).then(r=>r||new Response('离线且本页尚未缓存',{status:503}))));});",
        encoding="utf-8")
    print(json.dumps({"days": len(cur["days"]), "html": len(list(OUT.glob("day-*.html"))),
                      "questions_min": min(totals), "questions_max": max(totals)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
