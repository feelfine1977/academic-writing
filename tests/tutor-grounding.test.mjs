import test from 'node:test';
import assert from 'node:assert/strict';
import {guidanceMarkup,adviceCheckMarkup,reviewBasisMarkup,editAttemptsMarkup} from '../dist/tutor-grounding.js';
const esc=s=>String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));

test('private source and model strings stay text, including quotation and exclusion notices',()=>{
 const attack='<img src=x onerror=alert(1)>';
 const record={id:'rule',instruction:attack,evidence:[{title:attack,locator:attack,quote:attack}],not_applicable_when:[attack]};
 const packet={outline_focus:{selected:{title:attack}},grounding:{coaching_records:[record],notices:[attack],conflicts:[[attack,'rule']]}};
 for(const html of [guidanceMarkup(packet,esc),reviewBasisMarkup({basis_id:'rule'},{context:packet},esc),adviceCheckMarkup({alignment:{status:'checked',notice:attack,items:[{id:'priority-0',reason:attack,retained:false,comparison_flags:[{reason:attack}]}]}},esc)]){
  assert.ok(!html.includes('<img'));
  assert.ok(html.includes('&lt;img'));
 }
});

test('a completed comparison is never labelled supervisor approval and withheld edits explain why',()=>{
 const html=adviceCheckMarkup({alignment:{status:'checked',items:[{id:'suggestion-0',retained:false,reason:'Meaning changed',comparison_flags:[]}]},provenance:{model:'local-a'},check_provenance:{model:'local-b'}},esc);
 assert.match(html,/Some model feedback was withheld/);
 assert.match(html,/Meaning changed/);
 assert.match(html,/different local models/);
 assert.match(html,/Shared errors remain possible/);
 assert.doesNotMatch(html,/approved by your supervisor|Alignment passed/);
});

test('absent guidance is explicit and archived legacy requirements remain readable',()=>{
 assert.match(guidanceMarkup({grounding:{notices:['No private guidance available']}},esc),/No private guidance available/);
 const html=guidanceMarkup({grounding:{requirements:[{id:'old',instruction:'Keep clear wording',evidence:[]}]}},esc);
 assert.match(html,/Keep clear wording/);
 assert.equal(reviewBasisMarkup({basis_id:'invented'},{context:{grounding:{}}},esc),'');
});

test('failed repair is transparent and does not claim a second comparison ran',()=>{
 const job={operation:'selected_passage_edit',alignment:{status:'not_requested',notice:'No additional model comparison was run.'},edit_attempts:[
  {proposal:{suggestions:[{replacement:'<unsafe proposal>'}]},flags:[{reason:'Dropped the limitation'}]},
  {error:'<unavailable>'}
 ]};
 const html=adviceCheckMarkup(job,esc)+editAttemptsMarkup(job,esc);
 assert.match(html,/Requested edit/);
 assert.match(html,/one correction attempt/);
 assert.match(html,/Dropped the limitation/);
 assert.match(html,/&lt;unsafe proposal&gt;/);
 assert.match(html,/&lt;unavailable&gt;/);
 assert.doesNotMatch(html,/use the same local model|<unsafe proposal>|<unavailable>/);
 assert.equal(editAttemptsMarkup({edit_attempts:[{}]},esc),'');
});
