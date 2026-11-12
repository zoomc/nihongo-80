
(function(){'use strict';
var PREFIX='nh80.v9.pending.', LOCAL='nh80.v9.latest', SNAP='nh80.v9.study.snapshot', CATALOG='nh80.v15.catalog', study=read(SNAP,null),catalog=read(CATALOG,[]),busy=false,timer=null;
var $=function(s,r){return (r||document).querySelector(s)};
function esc(x){return String(x==null?'':x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}
function uid(){return (crypto.randomUUID?crypto.randomUUID():Date.now()+'-'+Math.random().toString(36).slice(2))}
function read(key,fallback){try{return JSON.parse(localStorage.getItem(key))||fallback}catch(e){return fallback}}
function pending(){return Object.keys(localStorage).filter(function(k){return k.indexOf(PREFIX)===0}).map(function(k){var x=read(k,null);return x?{key:k,value:x}:null}).filter(Boolean)}
function mergeRows(base,rows){
 var v=JSON.parse(JSON.stringify(base||{ratings:[],questions:[],plan:null}));v.ratings=v.ratings||[];v.questions=v.questions||[];
 rows.forEach(function(entry){var x=entry.value||entry;if(x.kind==='rating'){
  var r=x.review, old=v.ratings.find(function(y){return y.kid===r.kid});
  if(!old){old={kid:r.kid,ever_bad:0};v.ratings.push(old)}
  old.ever_bad=Boolean(old.ever_bad||r.rating==='again'||r.rating==='hard');old.rating=r.rating;old.day=r.day;old.created_at=x.created_at||old.created_at;
 }else if(x.kind==='attempt' && typeof x.correct==='boolean'){
  var row=v.questions.find(function(y){return y.qid===x.result.qid&&y.day===x.day});
  if(!row && !x.correct){row={qid:x.result.qid,day:x.day,knowledge_ids:x.knowledge_ids||[],wrong_count:0};v.questions.push(row)}
  if(row){row.last_correct=x.correct?1:0;if(!x.correct)row.wrong_count=(Number(row.wrong_count)||0)+1;if(!row.knowledge_ids.length)row.knowledge_ids=x.knowledge_ids||[]}
 }});return v;
}
function currentStudy(){return mergeRows(study,pending())}
function persistStudy(value){localStorage.setItem(SNAP,JSON.stringify(value));study=value}
function tell(message,isError){document.querySelectorAll('#studyStatus').forEach(function(el){el.textContent=message;el.classList.toggle('study-error',!!isError)})}
function queue(x){var key=PREFIX+uid();try{localStorage.setItem(key,JSON.stringify(x))}catch(e){tell('本机存储已满，记录未能保存，请清理空间后重试。',true);return false}schedule();return true}
function schedule(){clearTimeout(timer);timer=setTimeout(function(){flush()},600)}
function dayFor(kid){var page=Number(document.body.dataset.day)||0;if(page>=1&&page<=150)return page;var c=catalog.find(function(x){return (x.kid||x.id)===kid});var n=Number(localStorage.getItem('nh80.v5.lastDay'))||Number(c&&c.day)||0;return n>=1&&n<=150?n:0}
function updateLatest(kid,rating){var all=read(LOCAL,{});all[kid]=rating;try{localStorage.setItem(LOCAL,JSON.stringify(all))}catch(e){};paintBadges()}
function rate(kid,rating){if(!/^[VGK]\d{4}$/.test(kid)||['again','hard','good'].indexOf(rating)<0)return false;var day=dayFor(kid);if(!day){tell('缺少学习日，暂不能保存自评；请先打开对应课程。',true);return false}var item={kind:'rating',review:{event_id:'r-'+uid(),kid:kid,day:day,rating:rating}};if(!queue(item))return false;updateLatest(kid,rating);tell('已保存在本机。');renderPersonal();return true}
function attempt(q,answer,correct,details){details=details||{};var day=Number(q.day)||Number(document.body.dataset.day)||0;if(day<1||day>150)return false;var qid=q.qid||q.id;if(!qid)return false;
 var sessionKey='nh80.v5.session.'+day, session=sessionStorage.getItem(sessionKey);
 if(q._replay){session=q._replaySession||(q._replaySession='replay-'+uid())}
 else if(!session){session='web-'+day+'-'+uid();sessionStorage.setItem(sessionKey,session)}
 var item={kind:'attempt',day:day,session:session,correct:typeof correct==='boolean'?correct:null,knowledge_ids:Array.isArray(q.knowledge_ids)?q.knowledge_ids:[],result:{qid:qid,answer:String(answer),hinted:details.hinted===true,revealed_before_submit:details.revealed_before_submit===true,seconds:Number.isFinite(details.seconds)?Math.max(0,Math.min(86400,Math.round(details.seconds))):null}};
 if(!queue(item))return false;paintBadges();if(!$('#wrongDeck'))renderPersonal();tell('练习已保存在本机。');return true}
async function flush(){if(busy)return;var all=pending();if(!all.length)return;busy=true;
 try{persistStudy(mergeRows(study,all));all.forEach(function(x){localStorage.removeItem(x.key)});paintBadges();renderPersonal();}
 finally{busy=false}}
function exportPending(){var rows=pending().map(function(x){return x.value});var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({version:1,exported_at:new Date().toISOString(),pending:rows},null,2)],{type:'application/json'}));a.download='nihongo-pending.json';a.click();setTimeout(function(){URL.revokeObjectURL(a.href)},1000)}
function ratingButtons(kid){return '<div class="study-rates">'+[['again','忘了'],['hard','不熟'],['good','记得']].map(function(a){return '<button type="button" data-study-rate="'+a[0]+'" data-kid="'+esc(kid)+'">'+a[1]+'</button>'}).join('')+'</div>'}
function bindRates(root){root.querySelectorAll('[data-study-rate]').forEach(function(b){b.onclick=function(){rate(b.dataset.kid,b.dataset.studyRate)}})}
function paintBadges(){var study=currentStudy(),latest=read(LOCAL,{}),map={},focus={},recovered={};if(study){((study.plan||{}).focus||[]).forEach(function(x){if(x.kid&&Array.isArray(x.reasons))focus[x.kid]=x.reasons.join('、')});(study.questions||[]).forEach(function(q){(q.knowledge_ids||[]).forEach(function(k){map[k]='wrong'})});(study.ratings||[]).forEach(function(r){if(r.rating==='again'||r.rating==='hard')map[r.kid]=r.rating;else if(r.ever_bad){recovered[r.kid]=true;if(!map[r.kid])map[r.kid]='recovered'}})};Object.keys(latest).forEach(function(k){if(latest[k]==='again'||latest[k]==='hard')map[k]=latest[k]});document.querySelectorAll('[data-kid]').forEach(function(el){if(el.matches('button')||el.classList.contains('study-badge'))return;el.querySelectorAll(':scope > .study-badge').forEach(function(old){old.remove()});var x=map[el.dataset.kid];if(x==='again'||x==='hard'||x==='wrong'||x==='recovered'){var b=document.createElement('span');b.className='study-badge '+(x==='hard'?'hard':'');b.textContent=x==='again'?'忘了':x==='hard'?'不熟':x==='recovered'?'曾不熟 · 已复习':'曾错过';el.appendChild(b)}if(recovered[el.dataset.kid]&&x!=='recovered'){var h=document.createElement('span');h.className='study-badge hard';h.textContent='曾不熟 · 已复习';el.appendChild(h)}if(focus[el.dataset.kid]){var f=document.createElement('span');f.className='study-badge';f.textContent=focus[el.dataset.kid];el.appendChild(f)}})}
async function refresh(){try{if(!catalog.length){var cr=await fetch('/data/catalog.json');if(!cr.ok)throw Error('课程索引暂不可用');var loaded=await cr.json();if(!Array.isArray(loaded))throw Error('课程索引格式错误');catalog=loaded;try{localStorage.setItem(CATALOG,JSON.stringify(catalog))}catch(e){}}}catch(e){}paintBadges();renderScheduled();renderPersonal()}
function fnv(t){var s=String(t==null?'':t).normalize('NFKC').replace(/\s+/g,''),h=2166136261>>>0;for(var ch of s){h^=ch.codePointAt(0);h=Math.imul(h,16777619)>>>0}return h.toString(16)}
function deck(root,questions){if(!root)return;var filter='mixed',index=0,done={};function render(){var arr=questions.filter(function(q){return filter==='mixed'||q.group===filter});if(index>=arr.length)index=Math.max(0,arr.length-1);var q=arr[index];root.innerHTML='<div class="study-filters">'+[['mixed','全部'],['vocab','词汇'],['grammar','语法']].map(function(a){return '<button type="button" data-filter="'+a[0]+'" aria-pressed="'+(filter===a[0])+'">'+a[1]+'</button>'}).join('')+'</div>'+(q?'<div class="study-deck"><div class="study-muted">'+(index+1)+' / '+arr.length+' · 自选练习</div><p>'+esc(q.prompt)+'</p><div class="study-choices">'+(q.options||[]).map(function(o,i){return '<button type="button" class="study-choice" data-choice="'+i+'">'+esc(o)+'</button>'}).join('')+'</div><div class="study-feedback" aria-live="polite"></div></div><div class="study-bar"><button type="button" data-prev>上一题</button><button type="button" data-next>下一题</button></div>':'<p class="study-muted">当前没有这类练习。</p>');root.querySelectorAll('[data-filter]').forEach(function(b){b.onclick=function(){filter=b.dataset.filter;index=0;render()}});if(!q)return;root.querySelector('[data-prev]').onclick=function(){index=Math.max(0,index-1);render()};root.querySelector('[data-next]').onclick=function(){index=Math.min(arr.length-1,index+1);render()};root.querySelectorAll('[data-choice]').forEach(function(b){b.onclick=function(){if(done[q.qid])return;var answer=q.options[Number(b.dataset.choice)],ok=fnv(answer)===String(q.h);if(!attempt(q,answer,ok)&&Number(q.day||document.body.dataset.day)>0)return;done[q.qid]={answer:answer,ok:ok};root.querySelectorAll('[data-choice]').forEach(function(x){x.disabled=true;var v=q.options[Number(x.dataset.choice)];if(fnv(v)===String(q.h))x.classList.add('is-right')});if(!ok)b.classList.add('is-wrong');root.querySelector('.study-feedback').textContent=ok?'答对了。':'还不对，正确项已标出。'}});if(done[q.qid]){var saved=done[q.qid];root.querySelectorAll('[data-choice]').forEach(function(x){x.disabled=true;var v=q.options[Number(x.dataset.choice)];if(fnv(v)===String(q.h))x.classList.add('is-right');if(!saved.ok&&v===saved.answer)x.classList.add('is-wrong')});root.querySelector('.study-feedback').textContent=saved.ok?'答对了。':'还不对，正确项已标出。'}}render()}
var mask='all',personalFilter='wrong';
function card(c,showRate){var kid=c.kid||c.id,front=c.front||c.surface||c.pattern||c.char||'',back=c.back||c.meaning_zh||c.meaning||'',kana=c.kana||'';return '<article class="study-item" data-kid="'+esc(kid)+'"><p><small class="study-kind">'+(c.kind==='grammar'?'语法':c.kind==='kanji'?'汉字':'词汇')+' · Day '+esc(c.day||'')+'</small><span tabindex="0" data-side="ja">'+esc(front)+(kana?'　'+esc(kana):'')+'</span></p><p><span tabindex="0" data-side="zh">'+esc(back)+'</span></p>'+(showRate?ratingButtons(kid):'')+'</article>'}
function masking(root){if(!root)return;root.querySelectorAll('[data-side]').forEach(function(el){el.classList.toggle('study-masked',mask===el.dataset.side);el.onclick=function(){el.classList.toggle('study-peek')};el.onkeydown=function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();el.classList.toggle('study-peek')}}});root.querySelectorAll('[data-study-mask]').forEach(function(b){b.setAttribute('aria-pressed',String(mask===b.dataset.studyMask));b.onclick=function(){mask=b.dataset.studyMask;masking(root)}})}
function maskControls(){return '<div class="study-bar">'+[['all','显示全部'],['zh','遮中文'],['ja','遮日语']].map(function(x){return '<button type="button" data-study-mask="'+x[0]+'">'+x[1]+'</button>'}).join('')+'</div>'}
function renderUnit(){var root=$('#unitList'),unit=window.__UNIT__;if(!root||!unit)return;var items=unit.items||[],lastDay=0;root.innerHTML='<p class="study-muted">'+items.filter(function(c){return c.kind==='vocab'}).length+' 个词 · '+items.filter(function(c){return c.kind==='grammar'}).length+' 条语法</p>'+maskControls()+'<div class="study-list unit-grid">'+items.map(function(c){var heading=c.day!==lastDay?'<h3>Day '+c.day+'</h3>':'';lastDay=c.day;return heading+card(c,true)}).join('')+'</div>';masking(root);bindRates(root);paintBadges()}
function renderScheduled(message){
 var root=$('#scheduledReview');
 if(!root||!window.NHReview)return;
 try{
  NHReview.recover();
  var index=new Map(catalog.map(function(c){return [c.kid,c]}));
  var queue=NHReview.due().filter(function(x){return (index.get(x.kid)?.review_questions || []).length});
  var status=message?'<p class="small" role="status">'+esc(message)+'</p>':'';
  var heading='<h2>到期复习 <span class="count">'+queue.length+' 张</span></h2>';
  if(!catalog.length){
   root.innerHTML=heading+'<p>词表暂时无法读取，刷新页面后重试。</p>';return;
  }
  if(!queue.length){
   root.innerHTML=heading+status+'<p>今天没有到期卡。每日练习的首次作答会自动安排下一次复习。</p>'
    +'<p class="small">排期保存在当前浏览器。</p>';return;
  }
  var next=queue[0], card=index.get(next.kid);
  var variants=card.review_questions;
  var question=variants[(Math.max(0,next.step+1))%variants.length];
  root.innerHTML=heading+status+'<p class="small">答题结果用于更新当前浏览器的复习排期。</p>'
   +'<div class="study-deck"><p class="recall-prompt">'+esc(question.prompt)+'</p>'
   +'<div class="study-choices">'+question.options.map(function(option,i){
     return '<button type="button" class="study-choice" data-recall-choice="'+i+'">'+esc(option)+'</button>';
   }).join('')+'</div><p id="recallFeedback" role="status"></p>'
   +'<button type="button" class="btn" id="nextRecall" hidden>下一张</button></div>';
  var choices=Array.from(root.querySelectorAll('[data-recall-choice]'));
  var nextButton=$('#nextRecall',root), feedback=$('#recallFeedback',root);
  nextButton.onclick=function(){
   renderScheduled();
   var first=$('[data-recall-choice]',root);if(first)first.focus();
  };
  choices.forEach(function(button){
   button.onclick=function(){
    var correct=fnv(question.options[Number(button.dataset.recallChoice)])===question.h;
    try{
     var interval=NHReview.rate(card.kid,correct?'good':'again');
     choices.forEach(function(choice){
      choice.disabled=true;
      if(fnv(question.options[Number(choice.dataset.recallChoice)])===question.h)choice.classList.add('is-right');
     });
     if(!correct)button.classList.add('is-wrong');
     feedback.textContent=interval?(correct?'答对了。':'答错了，正确选项已标出。')+' 下次复习在 '+interval+' 天后。':'这张卡已复习。';
     nextButton.hidden=false;
     nextButton.textContent=queue.length===1?'查看复习结果':'下一张';
     nextButton.focus();
     if(personalFilter==='hard')renderPersonal();
    }catch(e){feedback.textContent='浏览器无法保存复习排期。'}
   };
  });
 }catch(e){root.innerHTML='<h2>到期复习</h2><p>浏览器无法保存复习排期。</p>'}
}
function renderPersonal(){
 var root=$('#personalReview');if(!root)return;
 var snapshot=currentStudy(), local=read(LOCAL,{});
 var ratings=Object.assign(Object.fromEntries(snapshot.ratings.map(function(r){return [r.kid,r.rating]})),local,
  window.NHReview?NHReview.ratings():{});
 var wrong=snapshot.questions.concat(window.NHReview?NHReview.wrongQuestions():[]);
 var ids=new Set(personalFilter==='wrong'?wrong.flatMap(function(q){return q.knowledge_ids||[]}):
  Object.keys(ratings).filter(function(k){return ratings[k]==='again'||ratings[k]==='hard'}));
 var items=catalog.filter(function(c){return ids.has(c.kid)});
 root.innerHTML='<div class="study-filters">'+[['wrong','曾错过'],['hard','忘了 / 不熟']].map(function(x){
  return '<button type="button" data-personal-filter="'+x[0]+'" aria-pressed="'+(personalFilter===x[0])+'">'+x[1]+'</button>';
 }).join('')+'</div><p id="studyStatus" role="status" class="small"></p>'
 +(items.length?maskControls()+'<div class="study-list">'+items.map(function(c){return card(c,true)}).join('')+'</div>'
   :'<p class="study-muted">当前没有记录。</p>')
 +(personalFilter==='wrong'&&wrong.length?'<div class="study-bar"><button type="button" data-retry>重练近期错题</button></div><div id="wrongDeck"></div>':'');
 root.querySelectorAll('[data-personal-filter]').forEach(function(b){
  b.onclick=function(){personalFilter=b.dataset.personalFilter;renderPersonal()};
 });
 masking(root);bindRates(root);paintBadges();
 var retry=$('[data-retry]',root);
 if(retry)retry.onclick=async function(){
  retry.disabled=true;
  try{
   var days=Array.from(new Set(wrong.map(function(q){return q.day}))).sort(function(a,b){return b-a}).slice(0,7);
   var data=await Promise.all(days.map(async function(d){
    var r=await fetch('/data/day-'+String(d).padStart(3,'0')+'.json');
    if(!r.ok)throw Error('题目暂不可用');return r.json();
   }));
   var wanted=new Set(wrong.map(function(q){return q.day+':'+q.qid})), questions=[];
   data.forEach(function(d){
    var seen=new Set();
    [].concat(d.questions||[],d.practice||[],d.unit_questions||[],d.quiz||[],d.sentences||[],
     (d.listening_material||{}).questions||[]).forEach(function(q){
     if(wanted.has(d.day+':'+q.qid)&&!seen.has(q.qid)){
      seen.add(q.qid);questions.push(Object.assign({day:d.day,group:'mixed'},q,{_replay:true}));
     }
    });
   });
   if(questions.length)deck($('#wrongDeck'),questions);
   else $('#wrongDeck').textContent='当前版本未找到这些历史题目。';
  }catch(e){$('#wrongDeck').textContent=e.message}finally{retry.disabled=false}
 };
}
function init(){deck($('#practiceDeck'),window.__PRACTICE__||((window.__UNIT__||{}).questions)||[]);renderUnit();refresh();if(pending().length)flush();window.addEventListener('online',flush)}
window.NHStudy={rate:rate,attempt:attempt,refresh:refresh,flush:flush};if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
