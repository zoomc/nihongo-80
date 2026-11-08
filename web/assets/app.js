
(function(){
'use strict';
if('serviceWorker' in navigator&&location.protocol.startsWith('http'))navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).catch(function(){});
var STORE='nh80.v5.';
function safe(t){return String(t==null?'':t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function focus(text){
  text=String(text||'');var terms=window.__FOCUS__||[];var out='',pos=0;
  while(pos<text.length){var found=-1,term='';terms.forEach(function(t){var at=text.indexOf(t,pos);if(at>=0&&(found<0||at<found||(at===found&&t.length>term.length))){found=at;term=t}});
    if(found<0){out+=safe(text.slice(pos));break}out+=safe(text.slice(pos,found))+'<strong class="today-focus">'+safe(term)+'</strong>';pos=found+term.length;
  }return out;
}
function reveal(el){el.classList.add('peek');if(el.classList.contains('mask'))el.setAttribute('aria-label','临时显示：'+el.textContent.trim());setTimeout(function(){el.classList.remove('peek');if(el.classList.contains('mask'))el.setAttribute('aria-label','内容已遮盖，按回车临时查看');else el.removeAttribute('aria-label')},3000)}
function setView(section,view){
  localStorage.setItem(STORE+'view.'+section,view);var root=$('#'+section);
  $$('[data-view-panel]',root).forEach(function(p){p.hidden=p.getAttribute('data-view-panel')!==view});
  $$('[data-view]',root).forEach(function(b){b.setAttribute('aria-pressed',String(b.getAttribute('data-view')===view))});
}
function initViews(){
  ['review','vocab'].forEach(function(id){if(!$('#'+id))return;setView(id,localStorage.getItem(STORE+'view.'+id)||'list')});
  $$('[data-view]').forEach(function(b){b.addEventListener('click',function(){setView(b.closest('section').id,b.getAttribute('data-view'))})});
  $$('[data-mask]').forEach(function(b){b.addEventListener('click',function(){setMode(b.getAttribute('data-mask'))})});
}
var LATEST_PAYLOAD=null;
var mode=localStorage.getItem(STORE+'mode')||'all';  // all|zh|ja|both
function $(s,r){return (r||document).querySelector(s)}
function $$(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))}
function applyMode(root){
  $$('[data-role]',root).forEach(function(el){
    if(el.closest('#grammar')){el.classList.remove('mask','peek');el.removeAttribute('tabindex');el.removeAttribute('role');el.removeAttribute('aria-label');return;}
    var role=el.getAttribute('data-role');
    var override=el.closest('[data-mode]');var active=override?override.getAttribute('data-mode'):mode;
    var hide=(active==='both')||(active==='zh'&&role==='zh')||(active==='ja'&&role==='ja');
    el.classList.toggle('mask',hide);if(hide){el.setAttribute('tabindex','0');el.setAttribute('role','button');el.setAttribute('aria-label','内容已遮盖，按回车临时查看')}else{el.removeAttribute('tabindex');el.removeAttribute('role');el.removeAttribute('aria-label')}
    el.classList.toggle('peek',!hide&&el.classList.contains('peek'));
    if(!hide) el.classList.remove('mask');
  });
  $$('[data-mask]').forEach(function(x){x.setAttribute('aria-pressed',String(x.getAttribute('data-mask')===mode))});
  var b=$('#modeBtn'); if(b) b.textContent={all:'遮盖：关',zh:'遮盖：中文',ja:'遮盖：日语',both:'遮盖：双向'}[mode];
}
function setMode(m){mode=m;$$('[data-mode]').forEach(function(c){c.setAttribute('data-mode',m)});localStorage.setItem(STORE+'mode',m);applyMode(document)}
var MASK_BOUND=false;
function initMask(){
  applyMode(document);
  if(MASK_BOUND)return;
  MASK_BOUND=true;document.addEventListener('keydown',function(e){if((e.key==='Enter'||e.key===' ')&&e.target.classList.contains('mask')){e.preventDefault();reveal(e.target)}});
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
    if(m)reveal(m);
  });
}
/* 复习 */
var reviewState={i:0,res:[]};
function initReview(){
  var box=$('#review');if(!box)return;
  var cards=window.__REVIEW__||[];var list=$('#reviewList');
  var idx=$('#rIdx'),front=$('#rFront'),back=$('#rBack'),bar=$('#rBar');
  if(!cards.length){list.innerHTML='<p class="hint">本课没有安排旧内容，直接开始今日新词。</p>';$('#reviewCard').innerHTML=list.innerHTML;return}
  function rate(kid,value){if(window.NHStudy)window.NHStudy.rate(kid,value);var existing=reviewState.res.find(function(x){return x.kid===kid});if(existing)existing.rating=value;else reviewState.res.push({kid:kid,rating:value});
    $$('.rRateList').forEach(function(b){if(b.getAttribute('data-kid')===kid)b.setAttribute('aria-pressed',String(b.getAttribute('data-rate')===value))});
  }
  cards.forEach(function(c,i){var row=document.createElement('div');row.className='study-row';row.setAttribute('data-kid',c.kid);
    row.innerHTML='<div class="study-ja" data-role="ja"><span class="list-word">'+focus(c.front)+'</span>'+(c.kana?'<span class="small kana-line">'+safe(c.kana)+'</span>':'')+'</div><div class="study-meaning" data-role="zh">'+safe(c.back)+'</div><div class="rating-row" aria-label="第'+(i+1)+'项复习自评">'+['again','hard','good'].map(function(value,j){return '<button type="button" class="btn small rRateList" data-kid="'+c.kid+'" data-rate="'+value+'" aria-pressed="false">'+['忘了','不熟','记得'][j]+'</button>'}).join('')+'</div>';
    list.appendChild(row);
  });
  $$('.rRateList',list).forEach(function(b){b.addEventListener('click',function(){rate(b.getAttribute('data-kid'),b.getAttribute('data-rate'))})});
  function render(){if(reviewState.i>=cards.length){front.textContent='本组已复习完';back.textContent='可切换列表查看，或继续今日新词。';idx.textContent=cards.length+' / '+cards.length;$('#rShow').disabled=true;$$('.rRate',box).forEach(function(b){b.disabled=true});return}
    var c=cards[reviewState.i];front.innerHTML=focus(c.front)+(c.kana?'<div class="small">'+safe(c.kana)+'</div>':'');back.textContent=c.back;idx.textContent=(reviewState.i+1)+' / '+cards.length;bar.style.width=(reviewState.i/cards.length*100)+'%';applyMode($('#reviewCard'));
  }
  $('#rShow').addEventListener('click',function(){reveal(back);reveal(front)});
  $$('.rRate',box).forEach(function(b){b.addEventListener('click',function(){if(reviewState.i<cards.length){rate(cards[reviewState.i].kid,b.getAttribute('data-rate'));reviewState.i++;render()}})});
  render();
}
/* 词卡 */
var vState={i:0,res:{}};
function initVocab(){
  var box=$('#vocab'); if(!box)return;
  var cards=JSON.parse(box.getAttribute('data-cards')||'[]');
  var coreCards=cards.filter(function(c){return !c.optional});var allCards=cards;cards=coreCards;
  var extra=$('#extraVocab');if(extra)extra.addEventListener('change',function(){cards=extra.checked?allCards:coreCards;vState.i=0;total.textContent=cards.length;render();renderList()});
  var cur=$('#vCur'), total=$('#vTotal'), area=$('#vArea');
  total.textContent=cards.length;
  function render(){
    $('#vNext').disabled=vState.i>=cards.length;$('#vPrev').disabled=vState.i<=0;
    if(vState.i>=cards.length){area.innerHTML='<p class="hint">必学词已看完；请在会话中用自己的话造句。</p>';return}
    var c=cards[vState.i];
    cur.textContent=vState.i+1;
    var ko=c.ko?'<div class="ko" data-role="zh">韩语参考'+(c.ko_status==='ai_gloss'?'（AI）':'')+'：'+safe(c.ko)+'</div>':'';
    var ex=c.ex?'<div class="ex"><span data-role="ja">'+focus(c.ex.ja)+'</span><br><span class="zh" data-role="zh">'+safe(c.ex.zh)+'</span></div>':'';
    area.innerHTML='<div class="vcard" data-mode="'+mode+'">'+
      '<button class="eye" type="button">切换遮盖</button>'+
      '<div class="surface" data-role="ja">'+safe(c.surface)+'</div>'+
      '<div class="kana" data-role="ja">'+safe(c.kana)+'</div>'+
      '<div class="meaning" data-role="zh">'+safe(c.meaning)+'</div>'+ko+ex+
      ('<div class="rating-row">'+['again','hard','good'].map(function(r,j){return '<button type="button" class="btn small card-rate" data-rate="'+r+'">'+['忘了','不熟','记得'][j]+'</button>'}).join('')+'</div>')+
      (c.audio?'<div class="row" style="margin-top:8px"><button class="btn" data-speak="'+safe(c.surface)+'">听发音</button></div>':'')+
      '</div>';
    area.querySelectorAll('.card-rate').forEach(function(b){b.onclick=function(){if(window.NHStudy)window.NHStudy.rate(c.id,b.dataset.rate)}});
    applyMode(area); initMask();
  }
  function renderList(){
    var list=$('#vocabList');list.innerHTML='';cards.forEach(function(c,i){var row=document.createElement('div');row.className='study-row';row.setAttribute('data-kid',c.id);
      row.innerHTML='<div class="study-ja" data-role="ja"><span class="list-word">'+focus(c.surface)+'</span><span class="kana-line small">'+safe(c.kana)+'</span></div><div class="study-meaning" data-role="zh">'+safe(c.meaning)+'</div><button class="btn speak" type="button" data-speak="'+safe(c.surface)+'" aria-label="朗读第'+(i+1)+'个词">朗读</button>'+
        '<details class="list-meta"><summary>例句与韩语参考</summary>'+(c.ex?'<p class="list-example"><span data-role="ja">'+focus(c.ex.ja)+'</span><br><span data-role="zh" class="small">'+safe(c.ex.zh)+'</span></p>':'')+(c.ko?'<p class="small" data-role="zh">韩语参考'+(c.ko_status==='ai_gloss'?'（AI）':'')+'：'+safe(c.ko)+'</p>':'')+'</details><div class="rating-row">'+['again','hard','good'].map(function(r,j){return '<button type="button" class="btn small new-rate" data-rate="'+r+'">'+['忘了','不熟','记得'][j]+'</button>'}).join('')+'</div>';row.querySelectorAll('.new-rate').forEach(function(b){b.onclick=function(){if(window.NHStudy)window.NHStudy.rate(c.id,b.dataset.rate)}});list.appendChild(row);
    });applyMode(list);
  }
  renderList();
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
  var lastPassage=null;
  qs.forEach(function(q,qi){
    var wrap=document.createElement('div'); wrap.className='q';
    var ph='';
    if(q.passage&&q.passage!==lastPassage){ph='<div class="passage" lang="ja">'+safe(q.passage)+'</div>';lastPassage=q.passage;}
    else if(q.passage){ph='<div class="small">（同上材料）</div>';}
    wrap.innerHTML=ph+(q.direction?'<p class="small">'+(q.direction==='zh-ja'?'选择对应的日语句子':'选择对应的中文意思')+'</p>':'')+'<div><strong>'+(qi+1)+'.</strong> '+safe(q.prompt)+'</div>';
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
        fb.textContent=ok?'答对了。':'本题未答对。正确答案：'+q.options[q.oh.indexOf(q.h)];
        wrap.appendChild(fb); done++; if(ok)right++;
        score.textContent=right+' / '+done;
        if(window.NHStudy)window.NHStudy.attempt(q,o,ok,{hinted:selector==='#listenQuiz'&&TRANSCRIPT_HINTED,revealed_before_submit:selector==='#listenQuiz'&&TRANSCRIPT_HINTED,seconds:Math.round((Date.now()-STARTED)/1000)});
        QUIZ_RESULTS.push({qid:q.qid,answer:o,seconds:Math.round((Date.now()-STARTED)/1000),hinted:selector==='#listenQuiz'&&TRANSCRIPT_HINTED,revealed_before_submit:selector==='#listenQuiz'&&TRANSCRIPT_HINTED});
      });
      opts.appendChild(lab);
    });
    wrap.appendChild(opts);
    box.appendChild(wrap);
  });
}
/* 句子理解：3题必做，7题拓展，均为选择题 */
function initSentences(){
  if(!$('#sentenceItems'))return;
  var items=window.__SENT__||[];var required=items.filter(function(q){return !q.optional}),extra=items.filter(function(q){return q.optional});
  $('#sentenceItems').setAttribute('data-qs',JSON.stringify(required));$('#sentenceExtra').setAttribute('data-qs',JSON.stringify(extra));
  initQuiz('#sentenceItems','#sentenceScore');initQuiz('#sentenceExtra','#sentenceExtraScore');
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
  return {v:1,practice_mode:'choice',day:Number(day),session:sessionStorage.getItem(STORE+'session.'+day)||('web-'+day+'-'+crypto.randomUUID()),minutes:null,ts:new Date().toISOString(),source:'web',results:QUIZ_RESULTS,
      review_ratings:[],
      sentences:[]};
}
/* 同步：只发原始事件，不发 correct */
function sync(payload){
  if(!sessionStorage.getItem(STORE+'access'))return Promise.reject(new Error('还未填写学习口令，请在保存设置中填写；也可直接导出作答带到会话'));
  return fetch('/api/events',{method:'POST',headers:{'content-type':'application/json','X-NH80-Key':sessionStorage.getItem(STORE+'access')||''},
    body:JSON.stringify(payload)}).then(function(r){if(!r.ok)throw new Error(r.status===401?'学习口令不正确，请重新输入':r.status===429?'云端保存预算已用完，请导出作答交给老师':'保存暂不可用，请重试或导出作答');return r.json()})
    .then(function(r){if(r.ok!==true)throw new Error('未确认保存');return r});
}
document.addEventListener('DOMContentLoaded',function(){
  initMask(); initReview(); initVocab(); initViews(); initQuiz('#quizItems','#score'); initQuiz('#listenQuiz','#listenScore');var tr=$('#transcript');if(tr)tr.addEventListener('toggle',function(){if(tr.open)TRANSCRIPT_HINTED=true}); initSentences(); initSpeak();
  var access=$('#accessKey');if(access){access.value=sessionStorage.getItem(STORE+'access')||'';access.addEventListener('input',function(){sessionStorage.setItem(STORE+'access',access.value.trim())})}
  var exportBtn=$('#exportAnswers');if(exportBtn)exportBtn.addEventListener('click',function(){
    var payload=LATEST_PAYLOAD||collectPayload();
    if(!payload){$('#saveStatus').textContent='先作答，再点击保存或导出。';return}
    var url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));var a=document.createElement('a');a.href=url;a.download='nihongo-day-'+payload.day+'.json';a.click();URL.revokeObjectURL(url);
  });
  var restart=$('#restartPractice');if(restart)restart.addEventListener('click',function(){sessionStorage.removeItem(STORE+'session.'+document.body.getAttribute('data-day'));location.reload()});
  var f=$('#finish');
  if(f)f.addEventListener('click',function(){
    var day=document.body.getAttribute('data-day');
    var payload=collectPayload();
    var pendingKey=STORE+'pending.'+day;
    var old=localStorage.getItem(pendingKey);
    if(old){try{
      var saved=JSON.parse(old);var valid=window.__QUIZ__.concat(window.__LISTEN__||[],window.__SENT__||[]).map(function(q){return q.qid});
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
    sync(payload).then(function(){localStorage.removeItem(pendingKey);f.textContent='作答已保存';$('#restartPractice').hidden=false;$('#saveStatus').textContent='已同步。会话读取后会核对必做题是否齐全、正确率是否达到70%。';localStorage.setItem(STORE+'lastDay',day);})
    .catch(function(e){f.disabled=false;f.textContent='保存失败，点击重试';$('#saveStatus').textContent=e.message+'。作答已暂存此设备。';});
  });
});
})();
