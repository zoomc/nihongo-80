
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
