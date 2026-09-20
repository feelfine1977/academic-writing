import test from 'node:test';
import assert from 'node:assert/strict';
import {SectionDraft,sectionScaffold,sectionSuggestion,hasOwnWritingGoal} from '../dist/section-writing.js';

const note=(hash='v1',prose='Original text.')=>({id:'section',hash,fields:{'Manuscript prose':prose,'Writing outline':'My plan.','Section manuscript source':'arguments'}});
const tick=()=>new Promise(resolve=>setImmediate(resolve));

test('a writing scaffold can seed only an empty draft and never replace authored prose',()=>{
 assert.equal(sectionScaffold({'Writing scaffold':'[Explain the context.]','Manuscript prose':''}),'[Explain the context.]');
 assert.throws(()=>sectionScaffold({'Writing scaffold':'New scaffold','Manuscript prose':'My own paragraph.'}),/already contains/);
 assert.throws(()=>sectionScaffold({'Manuscript prose':''}),/no writing scaffold/);
});

test('each unchanged suggestion remains applicable after another suggestion or unrelated manual edit',()=>{
 const job={text:'The first point is verbose. The next point is also verbose.'};
 const first={quote:'The first point is verbose.',replacement:'The first point is clear.'};
 const second={quote:'The next point is also verbose.',replacement:'The next point is concise.'};
 const a=sectionSuggestion(job,first,job.text);
 assert.equal(a.text,'The first point is clear. The next point is also verbose.');
 const b=sectionSuggestion(job,second,a.text);
 assert.equal(b.text,'The first point is clear. The next point is concise.');
 const manual=sectionSuggestion(job,second,'I changed the first idea. The next point is also verbose.');
 assert.equal(manual.text,'I changed the first idea. The next point is concise.');
 assert.match(manual.notice,/Other edits will be kept/);
});

test('changed, duplicate or out-of-selection quotations cannot replace another passage',()=>{
 const s={quote:'Same words.',replacement:'New words.'};
 assert.equal(sectionSuggestion({text:'Same words. Same words.'},s,'Same words. Same words.').text,undefined);
 assert.equal(sectionSuggestion({text:'Same words.'},s,'I changed these words.').text,undefined);
 assert.equal(sectionSuggestion({text:'Same words.'},s,'Same words. Same words.').text,undefined);
 assert.equal(sectionSuggestion({text:'Same words. Other words.',selected_text:'Other words.'},s,'Same words. Other words.').text,undefined);
 assert.equal(sectionSuggestion({text:'Same words.'},{quote:'Invented words.',replacement:'New text.'},'Same words.').text,undefined);
});

test('edits during an in-flight save are written against its returned revision without losing newer text',async()=>{
 const pending=[],cached=[],calls=[];
 const draft=new SectionDraft(note(),{cache:v=>{cached.push(v);return true},save:(base,fields)=>{calls.push({base,fields});return new Promise(resolve=>pending.push(resolve));}});
 draft.change('Manuscript prose','First revision.');
 const saving=draft.save();
 draft.change('Manuscript prose','Second revision while waiting.');
 draft.change('Writing outline','A new connection.');
 pending.shift()({...note('v2','First revision.')});await tick();
 assert.equal(calls.length,2);assert.equal(calls[1].base,'v2');
 assert.deepEqual(calls[1].fields,{'Manuscript prose':'Second revision while waiting.','Writing outline':'A new connection.'});
 pending.shift()({...note('v3','Second revision while waiting.'),fields:{...note().fields,'Manuscript prose':'Second revision while waiting.','Writing outline':'A new connection.'}});
 assert.equal(await saving,true);assert.equal(draft.values['Manuscript prose'],'Second revision while waiting.');assert.deepEqual(draft.dirty,{});assert.equal(cached.at(-1),null);
 assert.equal(draft.values['Section manuscript source'],'arguments');
});

test('reverting to the old text during a save is not lost when the newer server response arrives',async()=>{
 let finish;const calls=[];
 const draft=new SectionDraft(note(),{save:async(base,fields)=>{calls.push({base,fields});if(calls.length===1)return new Promise(resolve=>finish=resolve);return note('v3',fields['Manuscript prose']);}});
 draft.change('Manuscript prose','Temporary edit.');const saving=draft.save();draft.change('Manuscript prose','Original text.');
 finish(note('v2','Temporary edit.'));await saving;
 assert.equal(calls.length,2);assert.equal(calls[1].fields['Manuscript prose'],'Original text.');assert.equal(draft.note.fields['Manuscript prose'],'Original text.');
});

test('conflicts retain browser edits and stop automatic retry against the competing version',async()=>{
 let calls=0,recovery;
 const draft=new SectionDraft(note(),{cache:value=>{recovery=value;return true},save:async()=>{calls++;throw new Error('Vault changed elsewhere');}});
 draft.change('Manuscript prose','My unsaved text.');assert.equal(await draft.save(),false);
 draft.change('Writing outline','Another idea.');assert.equal(await draft.save(),false);
 assert.equal(calls,1);assert.equal(recovery.base_hash,'v1');assert.equal(recovery.fields['Manuscript prose'],'My unsaved text.');assert.equal(recovery.fields['Writing outline'],'Another idea.');
});

test('recovery from another base is visible but cannot silently overwrite a vault edit or protected guidance',async()=>{
 let calls=0;
 const draft=new SectionDraft(note('v2','A change from Windows.'),{cached:{base_hash:'v1',fields:{'Manuscript prose':'My Mac draft.','Writing scaffold':'Injected scaffold.'}},save:async()=>{calls++;return note();}});
 assert.equal(draft.values['Manuscript prose'],'My Mac draft.');assert.equal(draft.values['Writing scaffold'],undefined);assert.match(draft.error,/Compare/);assert.equal(await draft.save(),false);assert.equal(calls,0);
 assert.throws(()=>draft.change('Writing scaffold','Replacement'),/not editable/);
});

test('a cache with the same values does not block an unchanged newer vault version',async()=>{
 let calls=0;
 const draft=new SectionDraft(note('v2'),{cached:{base_hash:'v1',fields:{'Manuscript prose':'Original text.'}},save:async()=>{calls++;return note();}});
 assert.equal(draft.error,'');assert.equal(await draft.save(),true);assert.equal(calls,0);
});

test('section-writing routes survive planner task links', async()=>{
 const {plannerRoute}=await import('../dist/planner.js');
 const route='#section-writing/my-paper?section=introduction';
 assert.equal(plannerRoute(route),route);
 assert.equal(plannerRoute('https://example.com/'), '');
});


test('a custom writing goal resumes only in its own idea and stage',()=>{
 const fields={'Writing intention':'Clarify this link.','Writing goal origin':'own','Writing goal stage':'connect','Active writing idea':'intro'};
 assert.equal(hasOwnWritingGoal(fields,'intro','connect'),true);
 assert.equal(hasOwnWritingGoal(fields,'intro','polish'),false);
 assert.equal(hasOwnWritingGoal(fields,'method','connect'),false);
 assert.equal(hasOwnWritingGoal({...fields,'Writing goal origin':'outline'},'intro','connect'),false);
 assert.equal(hasOwnWritingGoal({'Writing intention':'Legacy intention'},'intro','connect'),false);
});
