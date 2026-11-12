#!/usr/bin/env python3
"""build_v5_site.py — v10 每日页：只留内容。

设计口径（2026-11-08，用户明确要求）：
- 顶部不要模式按钮 / 分钟数 / 分段导航 / 站点链接 / 提示文案；
- 新词与语法各自一个局部遮挡开关；
- 所有题合成一整块，直接列出，不翻页、不分段，按知识点去重并覆盖当天全部新词与语法；
- 中文上方给小号日语文字（假名 + ruby 注音），例句可发音；
- 底部只有一个「完成」按钮，上报当天学习情况到 /api/progress。

构建期生成全部 HTML；前端 app.js 只负责遮挡 / 朗读 / 判分 / 完成上报。
其余页面（首页、资源页、真人听力页、资料库、复习集、五日单元）保持不变。
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import ko_pron

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "knowledge/seeds"
OUT = ROOT / "web"
DATA = OUT / "data"


def read(name):
    return [json.loads(x) for x in (SEED / name).read_text(encoding="utf-8").splitlines() if x.strip()]


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def fnv(text):
    """与前端一致的 FNV-1a（按 Unicode 码点），答案只以哈希出现在公开页。"""
    h = 2166136261
    for ch in re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(text))):
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return format(h, "x")


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
.conn{font-size:13px;color:var(--muted);overflow-wrap:anywhere}
.ko-box{background:var(--bg);border:1px solid var(--line);padding:8px 10px;margin:8px 0;font-size:13px}
.gcard{border-top:1px dashed var(--line);padding:14px 0}
.gcard:first-child{border-top:0;padding-top:0}
.listen-box{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:14px}
audio{width:100%;margin:6px 0}
.passage{white-space:pre-line;padding:12px;background:var(--bg);border-radius:8px;margin-bottom:10px}
.q{border-top:1px dashed var(--line);padding:14px 0}
.q:first-child{border-top:0;padding-top:2px}
.q .prompt{font-size:15px;overflow-wrap:anywhere}
.q .opts{display:grid;gap:6px;margin-top:8px}
.opt{display:flex;gap:8px;align-items:flex-start;border:1px solid var(--line);border-radius:8px;
padding:8px;cursor:pointer;font-size:15px}
.opt input{margin-top:5px;flex:none}
.opt.correct{border-color:var(--ok);background:rgba(46,125,79,.08)}
.opt.wrong{border-color:var(--bad)}
.fb{font-size:13px;margin-top:6px}.fb.ok{color:var(--ok)}.fb.bad{color:var(--bad)}
.qscore{font-size:13px;color:var(--muted);margin-bottom:8px}
.foot{position:fixed;left:0;right:0;bottom:0;background:var(--surface);border-top:1px solid var(--line);
padding:10px 14px;display:flex;gap:10px;align-items:center;justify-content:center;z-index:30}
.foot .btn{flex:1;max-width:280px}
.foot .status{flex:1;max-width:320px;font-size:12px;color:var(--muted)}
details summary{cursor:pointer;color:var(--muted);font-size:13px}
.kstrip{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.kchip{font-size:13px;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:4px 8px}
.resource-link{display:block;padding:8px 0}.week-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px}
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
 var sb=e.target.closest('[data-show-all]');
 if(sb){showAll(sb);return}
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
 if(['all','zh','ja','both'].indexOf(saved)<0)saved='all';
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
# 新词区的顺序：平假读音 → 日语单词 → 韩语发音 → 中文 → 例句韩语读音 → 例句 → 朗读。
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
    """例句：韩语读音 → 日语（含当天词的 ruby）→ 中文 → 朗读。"""
    if not ex or not ex.get("ja"):
        return ""
    ja = ex.get("ja", "")
    ko_html = ('<div class="ex-ko" data-role="zh" lang="ko">%s</div>' % esc(ko)) if ko else ""
    return ('<div class="ex">%s'
            '<div class="ex-ja" data-role="ja">%s</div>'
            '<div class="ex-zh" data-role="zh">%s</div>'
            '<button class="speak" type="button" data-speak="%s">朗读</button>'
            '</div>' % (ko_html, ruby_text(ja, mapping), esc(ex.get("zh") or ""), esc(ja)))


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
        ex = (v.get("examples") or [{}])[0]
        ko = v.get("ko_hint") or v.get("ko_hanja") or ""
        tag = "" if vid in core else '<span class="small"> · 选学</span>'
        out.append(
            '<div class="item">'
            '<button class="show-all" type="button" data-show-all aria-label="临时显示三种语言 10 秒" hidden>显示</button>'
            '%s'
            '<div class="jp" data-role="ja">%s</div>'
            '%s'
            '<div class="zh" data-role="zh">%s%s</div>'
            '%s%s%s</div>'
            % (kana_line(surface, kana), jp_word(surface, kana),
               ko_read_line(ko_pron.pron(kana)), esc(v["meaning_zh"]), tag,
               ('<div class="ko" data-role="zh">韩语参考：%s</div>' % esc(ko)) if ko else "",
               example_html(ex, mapping, reader.hangul(ex.get("ja", ""))), rates_html(vid)))
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
        ko = ('<div class="ko-box" data-role="zh"><strong>朝鲜语：</strong>%s<br>'
              '<span class="small">%s</span></div>'
              % (esc(g["ko_equiv"]), esc(g.get("ko_diff", "")))) if g.get("ko_equiv") else ""
        usage = ('<div class="small" data-role="zh">%s</div>' % esc(g.get("usage", ""))) if g.get("usage") else ""
        trap = ('<details><summary>易错点</summary><p class="small">'
                '<span data-role="ja">%s → %s</span>'
                '<span data-role="zh">（%s）</span></p></details>'
                % (esc(err.get("wrong")), esc(err.get("fix")), esc(err.get("why")))) if err.get("wrong") else ""
        out.append(
            '<div class="gcard">'
            '<button class="show-all" type="button" data-show-all aria-label="临时显示三种语言 10 秒" hidden>显示</button>'
            '<div class="pattern" data-role="ja">%s</div>'
            '%s'
            '<div class="zh" data-role="zh">%s</div>'
            '<div class="conn" data-role="ja">%s</div>'
            '%s%s%s%s%s</div>'
            % (esc(pattern), ko_read_line(pattern_ko(g, reader)),
               esc(g["meaning_zh"]), esc(g.get("connection", "")),
               usage, exs, ko, trap, rates_html(gid)))
    return "".join(out) or '<p class="small">今天没有新语法。</p>'


# ---------------------------------------------------------------------------
# 一整块练习：以必做骨架为准，按知识点去重，补齐当天全部新词 + 新语法
# ---------------------------------------------------------------------------
def coverage_question(day, kid, vocab, grammar, all_rows):
    """为没有任何题覆盖的知识点补 1 题；只出「释义」或「假名」，不再叠加同考点。"""
    n = day
    rnd = random.Random(20261108 * 100 + n + int(kid[1:]))
    if kid.startswith("V"):
        v = vocab[kid]
        answer = v["meaning_zh"] if (n + int(kid[1:])) % 2 else v["kana"]
        cap = "meaning" if answer == v["meaning_zh"] else "reading"
        others = [x["meaning_zh"] if cap == "meaning" else x["kana"] for x in all_rows
                  if x["id"] != kid]
        stem = "「%s」的%s是？" % (v["surface"], "意思" if cap == "meaning" else "假名读音")
    else:
        g = grammar[kid]
        answer = g["meaning_zh"]
        cap = "meaning"
        others = [x["meaning_zh"] for x in grammar.values() if x["id"] != kid]
        stem = "句型「%s」的意思是？" % g["pattern"]
    rnd.shuffle(others)
    opts, seen = [answer], {answer}
    for o in others:
        if o and o not in seen and fnv(o) != fnv(answer):
            opts.append(o)
            seen.add(o)
        if len(opts) == 4:
            break
    if len(opts) < 4:
        return None
    rnd.shuffle(opts)
    qid = "X-%03d-%s-c" % (n, kid)
    return {"id": qid, "qid": qid, "type": "mcq", "day": n, "prompt": stem,
            "options": opts, "h": fnv(answer), "oh": [fnv(o) for o in opts],
            "knowledge_ids": [kid], "capability": cap, "group": "vocab" if kid.startswith("V") else "grammar",
            "optional": True}


def merge_questions(day, vocab, grammar, kanji, materials, sentence_rows):
    from quiz_v5 import day_questions, public_question
    from sentence_choices import build_for_day as sentence_questions
    from practice_v9 import build_daily

    n = day["day"]
    private = day_questions(day, vocab, grammar, kanji, materials)
    sentences = sentence_questions(day, sentence_rows)
    practice = build_daily(day, vocab, grammar, kanji)
    pool = {}
    for q in private + sentences + practice:
        pool.setdefault(q["qid"], public_question(q))

    required = list(day.get("question_ids") or [])
    selected, seen, kid_count = [], set(), defaultdict(int)

    def take(q):
        if not q or q["qid"] in seen:
            return
        assert "answer" not in q and "rationale" not in q, "公开题含明文答案 " + q["qid"]
        assert len(q["options"]) == 4 and q["h"] in q["oh"], q["qid"]
        selected.append(q)
        seen.add(q["qid"])
        for kid in q.get("knowledge_ids") or []:
            kid_count[kid] += 1

    # 1) 必做骨架（与 finish-day 门控一致）全部列出
    for qid in required:
        take(pool.get(qid))
    # 2) 其余题按知识点去重，每个知识点最多再补 1 题
    ordered = [pool[q["qid"]] for q in private + sentences + practice if q["qid"] in pool]
    for q in ordered:
        kids = q.get("knowledge_ids") or []
        if not kids:
            continue
        if any(kid_count[k] >= 2 for k in kids):
            continue
        take(q)
    # 3) 覆盖兜底：当天所有新词（含选学）与所有新语法都必须有题
    all_vocab = sorted(vocab.values(), key=lambda x: x["id"])
    targets = list(day["new_vocab_ids"]) + list(day["new_grammar_ids"])
    for kid in targets:
        if kid_count[kid]:
            continue
        q = coverage_question(n, kid, vocab, grammar, all_vocab)
        if q:
            take(q)
    missing = [k for k in targets if not kid_count[k]]
    assert not missing, "Day %d 缺少题目覆盖：%s" % (n, missing[:5])
    assert len({q["qid"] for q in selected}) == len(selected), "Day %d 题目重复" % n
    assert len(selected) <= 60, "Day %d 题量超出上报上限：%d" % (n, len(selected))
    return selected


def build_questions_html(questions):
    rows = []
    for i, q in enumerate(questions, 1):
        passage = ('<div class="passage" lang="ja">%s</div>' % esc(q["passage"])) if q.get("passage") else ""
        opts = "".join(
            '<label class="opt" data-oh="%s"><input type="radio" name="q%d"><span>%s</span></label>'
            % (esc(q["oh"][j]), i, esc(o)) for j, o in enumerate(q["options"]))
        rows.append('<div class="q" data-qid="%s" data-h="%s">%s<div class="prompt">%d. %s</div>'
                    '<div class="opts">%s</div></div>'
                    % (esc(q["qid"]), esc(q["h"]), passage, i, esc(q["prompt"]), opts))
    return "".join(rows)


def build_listen_html(listen_json, audio_manifest, materials):
    """听力音频与脚本放在练习块内，题目并入整块练习，不再单独成段。"""
    if not listen_json:
        return ""
    m = materials[listen_json["id"]]
    return ('<div id="listening" class="listen-box">'
            '<div class="small">今日听力 · 原创合成语音 · %s 秒</div>'
            '<audio controls preload="metadata" src="%s" aria-label="当天听力"></audio>'
            '<details><summary>核对听力脚本</summary><p lang="ja" class="passage">%s</p></details>'
            '<button class="speak" type="button" data-speak="%s">设备朗读全文</button>'
            '</div>'
            % (round(listen_json["duration_sec"], 1), esc(listen_json["audio_url"]),
               esc(listen_json["transcript"]), esc(m["audio_text"])))


def mask_switch(scope):
    return ('<div class="mask-switch" aria-label="%s遮盖">'
            '<button type="button" data-mask="all">显示</button>'
            '<button type="button" data-mask="zh">遮中文</button>'
            '<button type="button" data-mask="ja">遮日语</button>'
            '<button type="button" data-mask="both">双向</button></div>' % scope)


def day_page(d, review_html, vocab_html, grammar_html, listen_html, questions_html, page_meta):
    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<meta name="color-scheme" content="light dark">'
            '<title>Day %03d · %s | Nihongo 120</title>'
            '<link rel="icon" href="data:,"><link rel="stylesheet" href="assets/app.css"></head>'
            '<body data-day="%03d"><div class="wrap"><main>'
            '<h1 class="lesson">Day <b>%03d</b> · %s</h1>'
            '<section class="card" id="review"><h2>今日复习 <span class="count">先回忆再核对</span></h2>%s</section>'
            '<section class="card" id="vocab"><h2>今日新词 <span class="count">%d 个</span></h2>%s%s</section>'
            '<section class="card" id="grammar"><h2>今日语法 <span class="count">%d 条</span></h2>%s%s</section>'
            '<section class="card" id="questions"><h2>练习 <span class="count">%d 题</span></h2>'
            '<p class="small">先完成前 %d 道基础题，余题按薄弱项练习。</p>%s<div class="qscore" id="qscore"></div>%s</section>'
            '<div class="foot"><button class="btn primary" id="finish" type="button">完成</button>'
            '<span class="status" id="finishStatus" role="status" aria-live="polite"></span></div>'
            '</main></div>'
            '<script>window.__PAGE__=%s;</script><script src="assets/app.js"></script>'
            '</body></html>'
            % (d["day"], esc(d["theme"]), d["day"], d["day"], esc(d["theme"]),
               review_html, len(d["new_vocab_ids"]), mask_switch("新词"), vocab_html,
               len(d["new_grammar_ids"]), mask_switch("语法"), grammar_html,
               page_meta["total"], len(d["question_ids"]), listen_html, questions_html,
               json.dumps(page_meta, ensure_ascii=False)))


# ---------------------------------------------------------------------------
# 其它页面壳（复习集 / 五日单元）沿用共享 study.js
# ---------------------------------------------------------------------------
def study_page(title, body, day=0, unit=None):
    import study_ui
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="color-scheme" content="light dark"><title>' + esc(title) +
            ' · Nihongo 120</title><link rel="stylesheet" href="assets/app.css"></head>'
            '<body data-day="' + str(day) + '"><div class="wrap" style="max-width:920px"><main>'
            '<h1>' + esc(title) + '</h1>' + body + '</main></div>'
            '<script>window.__UNIT__=' + json.dumps(unit, ensure_ascii=False) +
            ';window.__PRACTICE__=' + json.dumps(unit["questions"] if unit else [], ensure_ascii=False) +
            '</script><script src="assets/study.js"></script></body></html>')


def main():
    import study_ui
    from quiz_v5 import public_question, listening_quiz, day_questions
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

    catalog = []
    for day in cur["days"]:
        for kid in day["new_vocab_ids"]:
            v = vocab[kid]
            catalog.append({"kid": kid, "front": v["surface"], "back": v["meaning_zh"],
                            "kana": v["kana"], "kind": "vocab", "day": day["day"]})
        for kid in day["new_grammar_ids"]:
            g = grammar[kid]
            catalog.append({"kid": kid, "front": g["pattern"], "back": g["meaning_zh"],
                            "kana": g.get("connection", ""), "kind": "grammar", "day": day["day"]})
        for kid in day["new_kanji_ids"]:
            k = kanji[kid]
            catalog.append({"kid": kid, "front": k["char"], "back": k["meaning_zh"],
                            "kana": "、".join(k.get("onyomi", [])), "kind": "kanji", "day": day["day"]})
    (DATA / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")

    (OUT / "review.html").write_text(study_page(
        "错题与复习集",
        '<p class="small">先练到期内容，再补薄弱项。自评只调整复习排期，不代表掌握。</p>'
        '<div id="personalReview"></div>'), encoding="utf-8")
    for end in range(5, len(cur["days"]) + 1, 5):
        unit = build_unit(end, cur["days"], vocab, grammar, kanji)
        unit["items"] = [x for x in catalog if end - 4 <= x["day"] <= end and x["kind"] != "kanji"]
        unit["questions"] = [public_question(q) for q in unit["questions"]]
        body = ('<p class="small">五天学过的词汇与语法完整清单，含选学词。</p>'
                '<div id="unitList"></div><section class="card"><h2>五日巩固 · 20 题</h2>'
                '<div id="practiceDeck"></div></section>')
        (OUT / ("unit-%03d.html" % end)).write_text(
            study_page("Day %d–%d · 五日复习" % (end - 4, end), body, end, unit), encoding="utf-8")

    totals = []
    for d in cur["days"]:
        n = d["day"]
        merged = merge_questions(d, vocab, grammar, kanji, materials, sentence_rows)
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
                           "audio": "tts"})
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

        listen_json = None
        listen_html = ""
        lqs = []
        if d.get("listening"):
            mids = d.get("material_ids") or []
            m = materials.get(mids[0]) if mids else None
            if m:
                lqs = [public_question(q) for q in listening_quiz(d, m)]
                audio = audio_manifest.get("items", {}).get(m["id"], {})
                valid = (audio.get("text_sha256") == hashlib.sha256(m["audio_text"].encode()).hexdigest()
                         and (OUT / str(audio.get("url", "")).lstrip("/")).is_file())
                if not valid:
                    raise ValueError("缺少匹配原稿的完整音频：" + m["id"])
                listen_json = {"id": m["id"], "title": m["title"], "audio_url": audio["url"],
                               "audio_kind": "synthetic", "transcript": m["text_ja"],
                               "duration_sec": audio["duration_sec"], "questions": lqs}
                listen_html = build_listen_html(listen_json, audio_manifest, materials)

        page_meta = {
            "day": n,
            "required_ids": d.get("core_vocab_ids") or [],
            "extra_ids": d.get("extension_vocab_ids") or [],
            "grammar_ids": d.get("new_grammar_ids") or [],
            "q_kids": {q["qid"]: q.get("knowledge_ids") or [] for q in merged},
            "total": len(merged),
        }
        lesson_tasks = []
        if d.get("practice_note"):
            note = '<p class="small">%s</p>' % esc(d["practice_note"])
            if d.get("early_audio"):
                note += '<button type="button" class="speak" data-speak="%s">设备朗读</button>' % esc(d["early_audio"])
            if n >= 90:
                note += '<p><a href="resources.html">打开 JLPT 官方样题与练习卷入口</a></p>'
            lesson_tasks.append(note)
        if d.get("reading_id"):
            reading = materials[d["reading_id"]]
            lesson_tasks.append(
                '<details><summary>精读 · %s</summary><p class="small">先读日文，用一句话复述主旨，圈出依据，再展开译文核对。</p>'
                '<p class="passage" lang="ja">%s</p><details><summary>核对中文</summary><p>%s</p></details></details>'
                % (esc(reading["title"]), esc(reading["text_ja"]), esc(reading["text_zh"])))
        page = day_page(d, build_review_html(d, vocab, grammar, kanji, reader),
                        build_vocab_html(d, vocab, kanji, reader), build_grammar_html(d, grammar, reader),
                        "".join(lesson_tasks) + listen_html, build_questions_html(merged), page_meta)
        (OUT / ("day-%03d.html" % n)).write_text(page, encoding="utf-8")
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
            "questions": merged, "listening_material": listen_json,
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    (OUT / "n3-mock.html").write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1"><title>N3 自测入口</title><h1>N3 自测</h1>'
        '<p>使用官方样题，答后对照答案。本站阶段练习不换算官方分数。</p>'
        '<a href="resources.html">打开官方听力、阅读与样题</a></html>', encoding="utf-8")
    (OUT / "manifest.webmanifest").write_text(json.dumps({
        "name": "Nihongo 120", "short_name": "Nihongo", "start_url": "/", "display": "standalone",
        "background_color": "#fbfaf7", "theme_color": "#b4472e",
        "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"}]},
        ensure_ascii=False), encoding="utf-8")

    links = ('<p><a id="resume" class="btn primary" href="day-001.html">开始或继续学习</a></p>'
             '<p><a href="review.html">错题与个人复习集</a> · '
             '<a href="listening.html">真人听力（免费资源与可播放开放音频）</a> · '
             '<a href="resources.html">N3 官方样题与资源</a> · '
             '<a href="library.html">原创听读资料</a></p>')
    for start in range(1, len(cur["days"]) + 1, 7):
        chunk = [d for d in cur["days"] if start <= d["day"] < start + 7]
        links += '<details%s><summary>第 %d 周 · Day %d–%d</summary><ul class="week-grid">%s</ul></details>' % (
            ' open' if start == 1 else '', (start - 1) // 7 + 1, start, chunk[-1]["day"],
            ''.join('<li><a href="day-%03d.html">Day %03d · %s</a></li>'
                    % (d["day"], d["day"], esc(d["theme"])) for d in chunk))
    links += ('<details><summary>五日复习单元 · 每5天一组</summary><ul class="week-grid">'
              + ''.join('<li><a href="unit-%03d.html">Day %d–%d · 完整复习</a></li>' % (n, n - 4, n)
                        for n in range(5, len(cur["days"]) + 1, 5)) + '</ul></details>')
    (OUT / "index.html").write_text(
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Nihongo 120</title><link rel="stylesheet" href="assets/app.css"></head>'
        '<body><div class="wrap"><main><h1>Nihongo 120</h1>'
        '<p class="small">120 天 · 每天约 60 分钟。Day 1–30 N5，31–60 N4，61–120 N3。</p>'
        + links + '</main></div><script>var n=Number(localStorage.getItem("nh80.v11.lastDay")||1);if(n>=1&&n<=120){'
                  'document.getElementById("resume").href="day-"+String(n).padStart(3,"0")+".html";}'
                  '</script></body></html>', encoding="utf-8")

    rdata = resource_sources()
    sources = rdata["sources"]
    inline = [x for x in sources if x.get("embed") == "inline"]
    links2 = [x for x in sources if x.get("embed") == "link" and x.get("free") is not False]
    rejected = [x for x in sources if x.get("embed") == "none"]
    honesty = ('<p class="small"><strong>使用边界：</strong>本站每日精听仍是 45 篇原创文本的合成语音（见 '
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
        '<title>真人听力 · Nihongo 120</title><link rel="stylesheet" href="assets/app.css"></head>'
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
    for level in ("N5", "N4", "N3"):
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
    revision = hashlib.sha256((CSS + JS + study_ui.CSS + study_ui.JS
                               + json.dumps(cur, ensure_ascii=False)).encode()).hexdigest()[:12]
    (OUT / "sw.js").write_text(
        "const C='nh80-v11-" + revision + "';self.addEventListener('install',e=>self.skipWaiting());"
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
