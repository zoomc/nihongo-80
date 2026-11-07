
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
  var lastPassage=null;
  qs.forEach(function(q,qi){
    var wrap=document.createElement('div'); wrap.className='q';
    var ph='';
    if(q.passage&&q.passage!==lastPassage){ph='<div class="passage" lang="ja">'+safe(q.passage)+'</div>';lastPassage=q.passage;}
    else if(q.passage){ph='<div class="small">（同上材料）</div>';}
    wrap.innerHTML=ph+'<div><strong>'+(qi+1)+'.</strong> '+safe(q.prompt)+'</div>';
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
