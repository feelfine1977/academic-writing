import test from 'node:test';
import assert from 'node:assert/strict';
import {writingStepGuide,writingStartMarkup} from '../dist/writing-start.js';
const esc=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');

test('the writing task follows the selected private outline rather than unrelated example data',()=>{
 const steps=[{id:'opening',title:'Food preservation',purpose:'Introduce the storage problem.',points:['Name the storage conditions.'],writing_guide:{goal:'Explain the storage problem.',write_now:['Describe how food is stored.','Name the observed limitation.'],reader_needs:'Why storage matters.',enough_for_now:'One connected start.',next:'Move to the comparison.'}},{title:'Comparing materials'}];
 const before=JSON.stringify(steps),g=writingStepGuide(steps[0],{steps});
 assert.equal(g.goal,'Explain the storage problem.');assert.deepEqual(g.write_now,['Describe how food is stored.','Name the observed limitation.']);assert.equal(g.next,'Move to the comparison.');assert.equal(g.custom,true);assert.equal(JSON.stringify(steps),before);
 const fallback=writingStepGuide(steps[1],{index:1,steps});
 assert.match(fallback.goal,/comparing materials/i);assert.equal(fallback.custom,false);assert.doesNotMatch(JSON.stringify(fallback),/observations need a question/);
});

test('older plans receive concrete existing points and neighbours without invented domain facts',()=>{
 const steps=[{title:'The problem',job:'Explain why a comparison is needed.',bullets:['State the cost.','Name the available material.'],bridge_to_next:'What can be compared?',boundary:'Do not invent results.'},{title:'Available approaches'}];
 const g=writingStepGuide(steps[0],{steps});
 assert.deepEqual(g.write_now,steps[0].bullets);assert.equal(g.reader_needs,steps[0].job);assert.match(g.next,/Available approaches/);assert.match(g.next,/What can be compared/);assert.equal(g.guardrail,'Do not invent results.');
});

test('revision and polish do not send the author back to a blank draft',()=>{
 const step={title:'Comparison',writing_guide:{goal:'Write the comparison.',write_now:['Start writing.']}};
 const rewrite=writingStepGuide(step,{stage:'rewrite'}),polish=writingStepGuide(step,{stage:'polish'});
 assert.match(rewrite.goal,/Revise/);assert.match(rewrite.enough_for_now,/do not need to restart/);assert.match(polish.goal,/Polish/);assert.match(polish.write_now.join(' '),/uncertainty/);assert.match(polish.enough_for_now,/same meaning/);
});

test('missing and malformed guide content uses readable bounded fallbacks',()=>{
 const g=writingStepGuide({writing_guide:{goal:{not:'text'},write_now:[null,{},'Usable action.']}},{stage:'unknown'});
 assert.equal(g.goal,'Write this part: Idea 1.');assert.deepEqual(g.write_now,['Usable action.']);assert.equal(g.stage,'connect');assert.ok(g.reader_needs);assert.ok(g.next);assert.doesNotMatch(JSON.stringify(g),/\[object Object\]/);
 assert.equal(writingStepGuide(null).title,'Idea 1');
});

test('guidance remains escaped teaching content and cannot inject HTML or manuscript text',()=>{
 const guide=writingStepGuide({title:'<script>bad()</script>',writing_guide:{write_now:['<img src=x onerror=bad()>'],reader_needs:'A & B.'}});
 const html=writingStartMarkup(guide,esc);
 assert.doesNotMatch(html,/<script>|<img/);assert.match(html,/&lt;script&gt;/);assert.match(html,/A &amp; B/);assert.match(html,/separate from your draft/);assert.match(html,/After this part/);assert.throws(()=>writingStartMarkup(guide),/escaping/);
});
