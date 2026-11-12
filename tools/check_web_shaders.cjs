#!/usr/bin/env node
// Audit the actual GLSL embedded in the shipped module, including engine shaders.
// Count whole rows per scalar/vector (deliberately pessimistic), matrix columns,
// complete dynamically indexed arrays, samplers, attributes and varying rows.
const fs = require('node:fs');
const path = require('node:path');
const {specializeUniforms} = require('../src/web_compat.js');

function audit(source, raw = false) {
  const s = raw ? source : specializeUniforms(source);
  const vertex = /gl_Position\s*=/.test(s);
  const structs = new Map([...s.matchAll(/struct (\w+)\s*\{([^}]+)\};/g)].map(m => [m[1], m[2]]));
  function fields(body) {
    return [...body.matchAll(/\b(\w+)(?:\[(\d+)\])?\s+(\w+)(?:\[(\d+)\])?\s*;/g)]
      .map(m => ({type:m[1], count:Number(m[2] || m[4] || 1), name:m[3]}));
  }
  function cost(type, count = 1) {
    if (structs.has(type)) return fields(structs.get(type)).reduce((a, f) => {
      const b = cost(f.type, f.count * count); return [a[0]+b[0],a[1]+b[1]];
    },[0,0]);
    if (/sampler/.test(type)) return [count, count];
    if (/^mat[234](?:x[234])?$/.test(type)) return [count * Number(type[3]), 0];
    if (/^(float|int|uint|bool|[biu]?vec[234])$/.test(type)) return [count, 0];
    throw Error('Unknown GLSL resource type: ' + type);
  }
  let rows = 0, samplers = 0;
  for (const m of s.matchAll(/^uniform\s+(?:(?:lowp|mediump|highp)\s+)?(\w+)(?:\[(\d+)\])?\s+(\w+)(?:\[(\d+)\])?;/gm)) {
    const [_, type, typeCount, name, nameCount] = m;
    const count = typeCount || nameCount;
    let c;
    if (structs.has(type) && name === 'u' && !raw) {
      c = fields(structs.get(type)).filter(f => new RegExp('\\bu\\.' + f.name + '\\b').test(s))
        .reduce((a, f) => { const b=cost(f.type,f.count); return [a[0]+b[0],a[1]+b[1]]; }, [0,0]);
    } else c = cost(type, Number(count || 1));
    rows += c[0]; samplers += c[1];
  }
  const varying = [...s.matchAll(new RegExp('^(?:flat )?' + (vertex?'out':'in') + ' (\\w+) v_\\w+;', 'gm'))]
    .reduce((a,m)=>a+cost(m[1])[0],0);
  const attributes = [...s.matchAll(/^layout\(location=(\d+)\) in (\w+) \w+;/gm)]
    .reduce((a,m)=>Math.max(a,Number(m[1])+cost(m[2])[0]),0);
  const errors=[];
  const limits={uniforms:vertex?256:224, samplers:16, varying:15, attributes:16};
  const counts={uniforms:rows,samplers,varying,attributes};
  for (const [key, limit] of Object.entries(limits)) if(counts[key]>limit) errors.push(`${key}: ${counts[key]} > ${limit}`);
  if (!/precision highp float;/.test(s)) errors.push('float precision is not explicitly highp');
  // The handwritten 2D shaders contain no integer uniforms or varyings.
  if (/\b(?:int|ivec[234]|uint|uvec[234])\b/.test(s) && !/precision highp int;/.test(s)) errors.push('int precision is not explicitly highp');
  const main = s.slice(s.lastIndexOf('void main'));
  const name = main.match(/\b(f_\w+)\(/)?.[1] || (vertex?'draw2d_vertex':'draw2d_fragment');
  return {name,stage:vertex?'vertex':'fragment',...counts,errors};
}

function shaders(file) {
  let data=fs.readFileSync(file);
  if (path.extname(file)==='.html') {
    const html=data.toString(), embedded=html.match(/const SLOPPY_WASM = "([^"]+)"/);
    if(embedded) data=Buffer.from(embedded[1],'base64');
    else {
      const name=html.match(/fetch\("(aegean\.[a-f0-9]+\.wasm)"\)/)?.[1];
      if(!name) throw Error('No packaged or embedded Wasm module');
      data=fs.readFileSync(path.join(path.dirname(file),name));
    }
  }
  const all=[...data.toString('latin1').matchAll(/#version 300 es\n[\x09\x0a\x0d\x20-\x7e]+/g)].map(m=>m[0]);
  if(all.length<2) throw Error('No generated GLSL found');
  return all;
}
module.exports={audit,shaders};
if(require.main===module){
  const raw=process.argv.includes('--raw'), file=process.argv[2];
  if(!file) throw Error('Usage: node tools/check_web_shaders.cjs site/index.html [--raw]');
  const result=shaders(file).map(s=>audit(s,raw));
  console.log(JSON.stringify(result,null,2));
  if(result.some(s=>s.errors.length)) process.exitCode=1;
}
