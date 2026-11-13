const assert = require('node:assert/strict');
const {specializeUniforms,chooseTier,cappedSize}=require('../src/web_compat.js');
const {audit}=require('./check_web_shaders.cjs');
const source=`#version 300 es
precision highp float;
precision highp int;
struct S_Params { vec4 tint_; vec4[240] bones_; };
uniform S_Params u;
out vec4 frag_color;
vec4 f_tint_1(vec4 p, S_Params l_u_1) { return p*l_u_1.tint_; }
vec4 f_main_2(S_Params l_u_2) { return f_tint_1(vec4(1.0), l_u_2); }
void main() { frag_color=f_main_2(u); }
`;
const s=specializeUniforms(source);
assert.equal(audit(source,true).errors.length,1);
assert.equal(audit(source).uniforms,1);
assert.equal(audit(source).errors.length,0);
assert.match(s,/f_tint_1\(vec4\(1.0\)\)/);
assert.match(s,/f_main_2\(\)/);
assert.doesNotMatch(s,/uniform.*bones/);
assert.equal(specializeUniforms(s),s);
const two=source.replace('f_main_2(S_Params l_u_2)', 'f_main_2(S_Params l_u_2, S_Params l_u_3)').replace('f_main_2(u);', 'f_main_2(u, u);');
assert.match(specializeUniforms(two),/frag_color=f_main_2\(\)/);
assert.throws(()=>specializeUniforms(source.replace('return p*l_u_1.tint_;','l_u_1.tint_ = p; return p;')),/Mutable/);
assert.throws(()=>specializeUniforms(source.replace('f_main_2(u);','f_main_2(other);')),/Non-global/);
assert.equal(chooseTier({mobile:true}),0);
assert.equal(chooseTier({mobile:true,override:'high'}),2);
assert.equal(chooseTier({renderer:'Intel UHD 620'}),1);
assert.equal(chooseTier({renderer:'NVIDIA',fragmentLimit:224}),0);
assert.equal(chooseTier({renderer:'NVIDIA',fragmentLimit:1024,textureLimit:8192}),2);
console.log('Web uniform specialization and quality selection passed');

// Changing the engine's rounded internal scale must not jitter a capped target.
const cap=cappedSize(2532,1170,844,390,230400);
assert.deepEqual(cap,[706,326]);
assert.deepEqual(cappedSize(1266,585,844,390,230400),cap);
assert.deepEqual(cappedSize(844,390,844,390,230400),cap);
assert.deepEqual(cappedSize(600,277,844,390,230400),[600,277]);
assert.deepEqual(cappedSize(1170,2532,390,844,230400),[326,706]);

// New compiler output may put the array size on its type rather than its name.
// Both forms must count all rows, including a shader that exceeds mobile limits.
for (const declaration of ['vec4[32] clouds', 'vec4 clouds[32]']) {
  const glsl=`#version 300 es\nprecision highp float;\nprecision highp int;\nuniform ${declaration};\nout vec4 color;\nvoid main(){color=clouds[0];}`;
  assert.equal(audit(glsl).uniforms,32);
  assert.equal(audit(glsl.replace(/32/g,'240')).errors.length,1);
}

// Scene resolution still follows the old cap/adaptive scale, while the HUD
// follows device pixels independently. Cover rotation, small windows and DPR.
const {resolutionPlan}=require('../src/web_compat.js');
for (const [cw,ch,dpr] of [[844,390,3],[390,844,3],[1280,720,1],[1920,1080,2],[320,240,1]]) {
  for (const mobile of [false,true]) for (const budget of [230400,518400,2600000]) {
    let previous;
    for (const adaptive of [1,.85,.72,.61,.52,.44]) {
      const top=Math.min(dpr,Math.sqrt(2600000/(cw*ch)));
      const d=Math.max(Math.min(top,1),top*adaptive);
      const w=Math.round(cw*d),h=Math.round(ch*d);
      const p=resolutionPlan(w,h,cw,ch,dpr,budget,mobile);
      const old=cappedSize(w,h,cw,ch,budget);
      assert(p.scene[0]<=old[0] && p.scene[1]<=old[1]);
      assert(p.display[0]*p.display[1]<= (mobile?1300000:2600000));
      if (previous) assert.deepEqual(p.display,previous);
      previous=p.display;
      assert(p.scale>0 && p.scale<=1);
    }
  }
}
const phone=resolutionPlan(2372,1096,844,390,3,230400,true);
assert.deepEqual(phone.scene,[706,326]);
assert.deepEqual(phone.display,[1677,775]);
console.log('Independent scene/HUD budgets passed');

assert.equal(resolutionPlan(1280,720,1280,720,1,2600000,false).scale,1);
