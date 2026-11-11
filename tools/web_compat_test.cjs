const assert = require('node:assert/strict');
const {specializeUniforms,chooseTier}=require('../src/web_compat.js');
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
