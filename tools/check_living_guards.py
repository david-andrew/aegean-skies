"""Conservative source call-graph check for explicit panics in the living frame paths.
It cannot prove absence of bounds/runtime failures; the recovery tests exercise actual mutations.
Run from anywhere. Unresolved callbacks/builtins are reported as outside this source graph.
"""
from pathlib import Path
import re,json,sys
root=Path(__file__).resolve().parents[1]/'src'
mods={}; nodes={}
# Erase comments and strings without changing line numbers. Avoid counting quoted prose as code.
def code_only(s):
 return re.sub(r'"(?:\\.|[^"\\])*"|#[^\n]*',lambda m:'\n'*m[0].count('\n'),s)
for p in sorted(root.glob('*.jo')):
 source=p.read_text(); modules=[]; aliases={}; imports={}
 for kind,file,alias in re.findall(r"^(use|import) '([^']+)'(?: as (\w+))?",source,re.M):
  target=(p.parent/file).resolve()
  if target.parent!=root or not target.exists():continue
  if kind=='use':modules.append(target.stem)
  else:aliases[alias or target.stem]=target.stem
 for file,names in re.findall(r"^from '([^']+)' import ([^\n]+)",source,re.M):
  target=(p.parent/file).resolve()
  if target.exists():
   for name in names.split(','):imports[name.strip()]=target.stem
 clean=code_only(source)
 matches=list(re.finditer(r'^(\w+) = \(',clean,re.M)); own={m[1] for m in matches}
 mods[p.stem]=(modules,aliases,imports,own)
 for i,m in enumerate(matches):
  body=clean[m.start():matches[i+1].start() if i+1<len(matches) else len(clean)]
  original=source.splitlines()[clean[:m.start()].count('\n'):clean[:(matches[i+1].start() if i+1<len(matches) else len(clean))].count('\n')+1]
  nodes[p.stem,m[1]]=(body,'\n'.join(original),clean[:m.start()].count('\n')+1)
roots=[('traffic','update_traffic'),('living_sim','minute_rules'),('living_scene','scene_motion'),('living_scene','scene_encounters'),('cargo_scene','step_cargo_scene'),('life_scene','step_life_scene'),('living_world','talk'),('living_world','reply'),('living_world','ask_for_work'),('living_world','apply_command')]
queue=list(roots);seen=set();problems=[];guarded=[]
while queue:
 mod,fn=queue.pop()
 if (mod,fn) in seen or (mod,fn) not in nodes:continue
 seen.add((mod,fn));body,original,line=nodes[mod,fn]
 if re.search(r'\b(?:assert|panic)\s*\(',body):
  if mod=='living_guard' and fn=='living_fault' and 'if _living_strict: panic(' in original:guarded.append(f'{mod}.{fn}')
  else:problems.append(dict(file=mod+'.jo',function=fn,line=line))
 uses,aliases,imports,own=mods[mod]
 for alias,name in re.findall(r'(?:(\b\w+)\.)?\b(\w+)\s*\(',body):
  if alias:
   target=aliases.get(alias)
   if target:queue.append((target,name))
  elif name in own:queue.append((mod,name))
  elif name in imports:queue.append((imports[name],name))
  else:
   for used in uses:
    if name in mods.get(used,([],{}, {},set()))[3]:queue.append((used,name))
result=dict(roots=['.'.join(r) for r in roots],reachable_functions=len(seen),strict_only_panics=guarded,unprotected_explicit_panics=problems,limitation='source-level approximation; not a proof about implicit bounds checks or arbitrary callbacks')
print(json.dumps(result,indent=2))
sys.exit(bool(problems))
