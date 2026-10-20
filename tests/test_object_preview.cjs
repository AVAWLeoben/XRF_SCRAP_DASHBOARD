// Test the shipped hover script with a minimal DOM/event host, without network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag) { this.tag=tag; this.style={}; this.children=[]; this.attrs={}; this.events={}; this.textContent=''; this.classList={contains:()=>false}; }
  setAttribute(k,v) { this.attrs[k]=v; }
  removeAttribute(k) { delete this.attrs[k]; if(k==='src') this.src=undefined; }
  append(...children) { this.children.push(...children); }
  appendChild(child) { this.children.push(child); return child; }
  addEventListener() {}
  getBoundingClientRect() { return {width:214,height:210}; }
  on(event,callback) { this.events[event]=callback; }
}
const graph=new Element('div');
graph.classList={contains: c=>c==='js-plotly-plot'};
const body=new Element('body'); body.children.push(graph);
const document={currentScript:{src:'https://example.org/repository/object_preview.js'}, body,
  children:[body], createElement:tag=>new Element(tag), addEventListener(){}};
let requests=[];
const context={document,URL,innerWidth:1200,innerHeight:800,WeakSet,Promise,Number,String,Math,
  setTimeout, setInterval(){}, requestAnimationFrame(){}, MutationObserver:class {observe(){}},
  fetch:async url=>{requests.push(String(url));return {ok:true,json:async()=>({images:{'1034':'data/Object_Images/60_1034.jpg'}})};}};
vm.runInNewContext(fs.readFileSync('object_preview.js','utf8'),context);
const tooltip=body.children.find(el=>el.id==='xrf-object-photo');
const photo=tooltip.children.find(el=>el.tag==='img');
const hover=(id,type='scatter')=>({points:[{data:{type},pointNumber:0,customdata:[id]}]});
(async()=>{
  assert.equal(requests.length,0,'No index or photo request at startup');
  assert.equal(photo.src,undefined);
  await graph.events.plotly_hover(hover(1034.1,'box'));
  assert.equal(requests.length,0,'Aggregate summaries must not load photos');
  const cancelled=graph.events.plotly_hover(hover(1034));
  graph.events.plotly_unhover();
  await cancelled;
  assert.equal(requests.length,0,'Quick sweeps must not load photos');
  await graph.events.plotly_hover(hover(1034.1));
  assert.equal(requests.length,1);
  assert.equal(requests[0],'https://example.org/repository/image-index.json');
  assert.equal(photo.src,'https://example.org/repository/data/Object_Images/60_1034.jpg');
  assert.equal(tooltip.children[0].textContent,'Object 1034');
  await graph.events.plotly_hover(hover(1034));
  assert.equal(requests.length,1,'Reuse index across hovers');
  await graph.events.plotly_hover(hover(999));
  assert.equal(photo.src,undefined);
  assert.equal(tooltip.children[3].textContent,'No photo available');
  graph.events.plotly_unhover();
  assert.equal(tooltip.style.display,'none');
  console.log('Lazy hover checks passed: no startup fetch, integer mapping, summary exclusion, missing photos and cancellation.');
})().catch(error=>{console.error(error);process.exitCode=1;});
