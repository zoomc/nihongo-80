
(function(){
'use strict';
window.mountLesson=function(root, DAY, meta, signal){
if(signal)signal.addEventListener('abort',function(){
 if(PEEK)clearInterval(PEEK.timer);
 if(window.speechSynthesis)window.speechSynthesis.cancel();
},{once:true});
var STORE='nh80.v11.';
function on(target,type,listener){target.addEventListener(type,listener,signal?{signal}:undefined)}
function $(s,r){return (r||root).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||root).querySelectorAll(s))}
function fnv(t){var s=String(t==null?'':t).normalize('NFKC').replace(/\s+/g,'');
 var h=2166136261>>>0;for(const ch of s){h^=ch.codePointAt(0);h=Math.imul(h,16777619)>>>0}return h.toString(16)}
function reveal(el){el.classList.add('peek');setTimeout(function(){el.classList.remove('peek')},3000)}
function applyScope(sec,mode){
 if(!sec)return;
 if(PEEK){clearInterval(PEEK.timer);PEEK.box.classList.remove('co-show');
  PEEK.btn.disabled=false;PEEK.btn.textContent=PEEK.label;PEEK=null}
 $$('[data-role]',sec).forEach(function(el){
  var r=el.getAttribute('data-role');
  var hide=mode===r;
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
on(root,'change',function(e){
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
on(root,'click',function(e){
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
on(root,'keydown',function(e){
 if((e.key==='Enter'||e.key===' ')&&e.target.classList&&e.target.classList.contains('mask')){
  e.preventDefault();reveal(e.target)}
});
['vocab','grammar'].forEach(function(id){var s=$('#'+id);if(!s)return;
 var saved='all';try{saved=localStorage.getItem(STORE+'mask.'+id)||'all'}catch(e){}
 if(['all','zh','ja'].indexOf(saved)<0)saved='all';
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
function finishLinks(){
 var status=$('#finishStatus');
 if(!status)return;
 var next=window.NHCourse?.next();
 status.textContent='学习情况已保存。';
 if(next){
  var label='Day '+String(next).padStart(3,'0'),link=document.createElement('a');
  link.href='/day-'+label.slice(4)+'.html';link.textContent='开始下一课 · '+label;
  status.append(' ',link);
 }
}
if(f&&window.NHCourse?.done(DAY)&&QUESTIONS.length===Object.keys(RESULTS).length){
 f.disabled=true;f.textContent='已完成';finishLinks();
}
if(f)f.addEventListener('click',function(){
 var qs=Object.values(RESULTS);
 if(qs.length!==QUESTIONS.length||!qs.length){$('#finishStatus').textContent='还有 '+(QUESTIONS.length-qs.length)+' 道单选题待作答。';return}
 var right=qs.filter(function(x){return x.correct}).length;
 var wrong=qs.filter(function(x){return !x.correct}).map(function(x){
  return {qid:x.qid,knowledge_ids:(meta.q_kids||{})[x.qid]||[]}});
 var payload={v:4,day:DAY,completed_at:new Date().toISOString(),
  required_ids:meta.required_ids||[],extra_ids:meta.extra_ids||[],grammar_ids:meta.grammar_ids||[],
  questions:qs,accuracy:qs.length?right/qs.length:0,self_rating:RATINGS,
  wrong_summary:wrong,
  review_summary:Object.keys(RATINGS).filter(function(k){return RATINGS[k]!=='good'}),
  note:''};
 document.documentElement.dataset.savingLesson='1';
 f.disabled=true;f.textContent='正在保存…';
 var status=$('#finishStatus');if(status)status.textContent='';
 fetch('/api/progress',{method:'POST',headers:{'content-type':'application/json'},
  body:JSON.stringify(payload)}).then(function(r){return r.json().then(function(d){
   if(!r.ok||d.ok!==true)throw new Error(d.reason||('HTTP '+r.status));return d})})
  .then(function(){saveLocal();try{localStorage.setItem('nh80.completed.'+DAY,'1')}catch(e){}
   window.NHCourse?.finish(DAY);
   f.textContent='已完成';finishLinks();})
  .catch(function(e){f.disabled=false;f.textContent='完成';
   if(status)status.textContent='云端暂不可用（'+e.message+'）；记录已留在本机。'})
  .finally(function(){delete document.documentElement.dataset.savingLesson});
});
};
if(!document.querySelector('.app-nav'))window.mountLesson(document,Number(document.body.dataset.day)||0,window.__PAGE__||{});
})();
