
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
 $$('[data-role]',sec).forEach(function(el){
  var r=el.getAttribute('data-role');
  var hide=(mode==='both')||(mode==='zh'&&r==='zh')||(mode==='ja'&&r==='ja');
  el.classList.toggle('mask',hide);if(!hide)el.classList.remove('peek');
  if(hide){el.setAttribute('tabindex','0');el.setAttribute('aria-label','内容已遮盖，点击临时查看')}
  else{el.removeAttribute('tabindex');el.removeAttribute('aria-label')}
 });
 $$('.mask-switch button',sec).forEach(function(b){
  b.setAttribute('aria-pressed',String(b.getAttribute('data-mask')===mode))});
 try{localStorage.setItem(STORE+'mask.'+sec.id,mode)}catch(e){}
}
var RESULTS={},RATINGS={},STARTED=Date.now();
function saveLocal(){try{localStorage.setItem(STORE+'state.'+DAY,JSON.stringify({results:RESULTS,ratings:RATINGS}))}catch(e){}}
function restore(){try{var s=JSON.parse(localStorage.getItem(STORE+'state.'+DAY)||'null');
 if(s&&s.results)RESULTS=s.results||{};if(s&&s.ratings)RATINGS=s.ratings||{};}catch(e){}
 Object.keys(RESULTS).forEach(function(qid){
  var wrap=$('.q[data-qid="'+qid+'"]');if(!wrap)return;
  var r=RESULTS[qid];wrap.setAttribute('data-done','1');
  $$('.opt',wrap).forEach(function(x){x.querySelector('input').disabled=true;
   if(x.getAttribute('data-oh')===wrap.getAttribute('data-h'))x.classList.add('correct');
   if(!r.correct&&x.querySelector('span').textContent===r.answer)x.classList.add('wrong')});
  var fb=document.createElement('div');fb.className='fb '+(r.correct?'ok':'bad');
  fb.textContent=r.correct?'答对了。':'本题未答对，正确项已标绿。';wrap.appendChild(fb);
 });
 Object.keys(RATINGS).forEach(function(kid){$$('[data-rate][data-kid="'+kid+'"]').forEach(function(b){
  b.setAttribute('aria-pressed',String(b.getAttribute('data-rate')===RATINGS[kid]))})});
 updateScore();
}
function updateScore(){var all=$$('.q'),done=Object.keys(RESULTS).length,
 right=Object.keys(RESULTS).filter(function(k){return RESULTS[k].correct}).length;
 var el=$('#qscore');if(el)el.textContent='已答 '+done+' / '+all.length+'　答对 '+right}
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
 var m=e.target.closest('.mask');if(m){reveal(m);return}
 var sp=e.target.closest('[data-speak]');
 if(sp){speak(sp.getAttribute('data-speak'),sp);return}
 var rt=e.target.closest('[data-rate]');
 if(rt){var kid=rt.getAttribute('data-kid'),v=rt.getAttribute('data-rate');RATINGS[kid]=v;
  $$('[data-rate][data-kid="'+kid+'"]').forEach(function(b){b.setAttribute('aria-pressed',String(b===rt))});
  saveLocal();return}
 var lab=e.target.closest('.q .opt');
 if(lab){
  var wrap=lab.closest('.q');if(wrap.getAttribute('data-done'))return;
  wrap.setAttribute('data-done','1');
  var answer=lab.querySelector('span').textContent;
  var ok=fnv(answer)===wrap.getAttribute('data-h');
  lab.classList.add(ok?'correct':'wrong');
  $$('.opt',wrap).forEach(function(x){x.querySelector('input').disabled=true;
   if(x.getAttribute('data-oh')===wrap.getAttribute('data-h'))x.classList.add('correct')});
  var fb=document.createElement('div');fb.className='fb '+(ok?'ok':'bad');
  fb.textContent=ok?'答对了。':'本题未答对，正确项已标绿。';wrap.appendChild(fb);
  RESULTS[wrap.getAttribute('data-qid')]={qid:wrap.getAttribute('data-qid'),answer:answer,
   correct:ok,hinted:false,revealed:false,seconds:Math.round((Date.now()-STARTED)/1000)};
  saveLocal();updateScore();return}
});
document.addEventListener('keydown',function(e){
 if((e.key==='Enter'||e.key===' ')&&e.target.classList&&e.target.classList.contains('mask')){
  e.preventDefault();reveal(e.target)}
});
['vocab','grammar'].forEach(function(id){var s=$('#'+id);if(!s)return;
 var saved='all';try{saved=localStorage.getItem(STORE+'mask.'+id)||'all'}catch(e){}
 applyScope(s,saved)});
restore();
var f=$('#finish');
if(f)f.addEventListener('click',function(){
 var meta=window.__PAGE__||{},qs=Object.keys(RESULTS).map(function(k){return RESULTS[k]});
 var right=qs.filter(function(x){return x.correct}).length;
 var wrong=qs.filter(function(x){return !x.correct}).map(function(x){
  return {qid:x.qid,knowledge_ids:(meta.q_kids||{})[x.qid]||[]}});
 var payload={v:2,day:DAY,completed_at:new Date().toISOString(),
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
  .then(function(){saveLocal();try{localStorage.setItem(STORE+'lastDay',String(DAY))}catch(e){}
   f.textContent='已完成';if(status)status.textContent='学习情况已保存，会话可读取。'})
  .catch(function(e){f.disabled=false;f.textContent='完成';
   if(status)status.textContent='云端暂不可用（'+e.message+'）；记录已留在本机。'});
});
})();
