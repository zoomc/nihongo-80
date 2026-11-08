"""Small, explicit highlighting rules; return escaped text with non-overlapping strong spans."""
import html
import re

def terms_for_day(day,vocab,grammar,kanji):
    terms=set()
    forms={'う':('い','って','った','わない'),'く':('き','いて','いた','かない'),
           'ぐ':('ぎ','いで','いだ','がない'),'す':('し','して','した','さない'),
           'つ':('ち','って','った','たない'),'ぬ':('に','んで','んだ','なない'),
           'ぶ':('び','んで','んだ','ばない'),'む':('み','んで','んだ','まない'),
           'る':('り','って','った','らない')}
    for vid in day['new_vocab_ids']:
        v=vocab[vid];word=v['surface'];terms.add(word)
        if len(v.get('kana',''))>=2:terms.add(v['kana'])
        if ('動詞' in v.get('pos','') or '动词' in v.get('pos','')) and len(word)>1:
            stem=word[:-1]
            if word.endswith('る') and ('一段' in v.get('pos','') or ('五段' not in v.get('pos','') and word.endswith(('える','いる')))):
                terms.update(stem+s for s in ('ます','ました','て','た','ない'))
            else:
                for i,suffix in enumerate(forms.get(word[-1],())):
                    terms.add(stem+suffix+('ます' if i==0 else ''))
        if word.endswith('い') and len(word)>1:
            terms.update(word[:-1]+s for s in ('く','かった','くない'))
    for gid in day['new_grammar_ids']:
        pattern=grammar[gid]['pattern']
        # Avoid treating grammatical meta words as Japanese learning spans.
        for chunk in re.findall(r'[ぁ-ゖァ-ヺ一-龯ー]+',pattern):
            if len(chunk)>=2 and chunk not in ('名詞','動詞','形容詞','普通形','辞書形','过去','现在','名词','动词'):
                terms.add(chunk)
                if chunk.endswith('る'):
                    terms.update(chunk[:-1]+suffix for suffix in ('ます','ました','ません','た','て','ない','れば','よう'))
                if chunk.endswith('う'):
                    terms.update(chunk[:-1]+suffix for suffix in ('います','いました','いません','った','って','わない'))
                if chunk.endswith('ない'):
                    terms.update(chunk[:-2]+suffix for suffix in ('なかった','なくて','なければ'))
                if chunk == 'です':terms.update(('でした','ではありません','じゃありません'))
                if chunk == 'ます':terms.update(('ました','ません','ませんでした'))
    terms.update(kanji[k]['char'] for k in day['new_kanji_ids'])
    return sorted((t for t in terms if t),key=lambda t:(-len(t),t))

def emphasize(text,terms):
    text=str(text or '')
    if not terms:return html.escape(text,quote=True)
    pattern='|'.join(re.escape(t) for t in sorted(set(terms),key=lambda t:(-len(t),t)))
    out=[];cursor=0
    for match in re.finditer(pattern,text):
        out.append(html.escape(text[cursor:match.start()],quote=True))
        out.append('<strong class="today-focus">'+html.escape(match.group(),quote=True)+'</strong>')
        cursor=match.end()
    out.append(html.escape(text[cursor:],quote=True))
    return ''.join(out)
