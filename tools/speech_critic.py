from pathlib import Path
from collections import Counter,defaultdict
import re,json,sys
source=Path(sys.argv[1])
root=Path(__file__).resolve().parents[1]
content=(root/'src/living_content.jo').read_text()
names=[]
for full in re.findall(r'PersonSeed\(\d+, "([^"]+)"',content):
    names.extend([full,full.split()[0]])
seed=(root/'src/living_life_seed.jo').read_text()
if m:=re.search(r'names = \[(.*?)\]',seed): names.extend(re.findall(r'"([^"]+)"',m[1]))
names=[x for x in names if x not in ('The','The Pilot','pilot')]
places=re.findall(r'"([^"]+)"',(content.split('PLACE_NAMES:')[1]).split('\n')[0])
goods=['fish','wine','oil','grain','fuel','parts','medicine','tobacco','arms']
craft=['Gull','Heron','Corsair','Falco','Tern','Petrel','Osprey','Swift','Pelican','Kite','Ibis','Kestrel','Minnow','Albatross','Cormorant','Kingfisher']
# Strong particulars: proper entities, real commodities/types, dates/numbers and anchored events.
# Generic "day", "weather", "boat", "someone", "here" alone never count.
entity=re.compile(r'\b(?:'+ '|'.join(re.escape(s) for s in sorted(set(names+places+goods+craft),key=len,reverse=True))+r')\b',re.I)
time=re.compile(r'\b\d+(?:[.:]\d+)?\b|\byesterday\b|\bSunday\b',re.I)
relation=re.compile(r"\b(?:remember|forgotten|know you|we(?:'ve| have) met|old acquaintance|kept (?:your|me)|owe me|forgive|trust you|don't know you|met before|we left off|come back|back again|we meet again)\b",re.I)
line_re=re.compile(r'^(.*?) \[(.*?) -> (.*?), (\w+)\]: (.*)$')
turns=[]; minute=0; day=0; last_speaker=None; last_body_grounded=False; seen=defaultdict(list); forbidden=[]
for raw in source.read_text().splitlines():
    if m:=re.match(r'DAY (\d+):',raw): day=int(m[1])-1
    if m:=re.match(r'-- (\d+):(\d+) --',raw): minute=day*1440+int(m[1])*60+int(m[2])
    m=line_re.match(raw)
    if m:
        speaker,voice,listener,topic,text=m.groups()
        last_speaker=(speaker,voice,listener)
    elif last_speaker and raw.startswith('  [') and '] ' in raw:
        speaker,voice,listener=last_speaker; topic='reply'; text=raw.split('] ',1)[1]
    elif last_speaker and raw.startswith('  ') and not raw.startswith('  ['):
        speaker,voice,listener=last_speaker; topic='question'; text=raw.strip()
    else: continue
    concrete=bool(entity.search(text) or time.search(text))
    # Report literal particulars separately from deliberate social acts. Reciprocal questions
    # qualify only in a conversation whose preceding body has a particular or named addressee.
    addressee = ('pilot' if listener == 'The Pilot' else listener.split()[0]).lower()
    addressed = bool(re.search(r'\b'+re.escape(addressee)+r'\b',text.lower()))
    social = topic in ('greeting','farewell','reply') and bool(relation.search(text) or addressed)
    if topic == 'question': social = last_body_grounded and bool(re.search(r"\b(?:you|your|company|news)\b",text,re.I))
    if topic not in ('question','reply'): last_body_grounded = concrete or social
    for old_min,old in seen[speaker]:
        if minute-old_min<240 and old==text: forbidden.append({'speaker':speaker,'minute':minute,'text':text})
    seen[speaker]=[(t,s) for t,s in seen[speaker] if minute-t<240]+[(minute,text)]
    turns.append(dict(speaker=speaker,voice=voice,topic=topic,text=text,concrete=concrete,social=social))
words=[re.findall(r"[a-z]+(?:'[a-z]+)?|\d+",t['text'].lower()) for t in turns]
ngrams={n:Counter(tuple(w[i:i+n]) for w in words for i in range(len(w)-n+1)) for n in (3,5)}
by=defaultdict(list)
for t in turns: by[t['topic']].append(t)
result={'file':source.name,'turns':len(turns),'concrete_percent':round(100*sum(t['concrete'] for t in turns)/max(1,len(turns)),2),'social_only_percent':round(100*sum(t['social'] and not t['concrete'] for t in turns)/max(1,len(turns)),2),'concrete_or_relationship_social_percent':round(100*sum(t['concrete'] or t['social'] for t in turns)/max(1,len(turns)),2),'forbidden_repeat_count':len(forbidden),'distinct_3gram_percent':round(100*len(ngrams[3])/max(1,sum(ngrams[3].values())),2),'distinct_5gram_percent':round(100*len(ngrams[5])/max(1,sum(ngrams[5].values())),2),'most_repeated_5grams':[{'phrase':' '.join(k),'count':v} for k,v in ngrams[5].most_common(15)],'by_topic':{k:{'turns':len(v),'grounded_percent':round(100*sum(t['concrete'] or t['social'] for t in v)/len(v),2)} for k,v in sorted(by.items())},'filler_samples':[t for t in turns if not(t['concrete'] or t['social'])][::max(1,len(turns)//30)][:20]}
print(json.dumps(result,indent=2))
