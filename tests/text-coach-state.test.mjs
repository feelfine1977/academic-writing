import test from 'node:test';
import assert from 'node:assert/strict';
import {discussionScope,proposedText,proposalState,recoverDiscussion} from '../dist/text-coach-state.js';
test('selection advice replaces only its original occurrence in the full paragraph',()=>{
 const text='📌 We have to check. They have to wait.',start=text.indexOf('They');
 const snapshot=discussionScope(text,start,text.length),option={quote:'have to',replacement:'need to',span:{start:5,end:12}};
 const r=proposedText(snapshot,option,text);
 assert.equal(r.text,'📌 We have to check. They need to wait.');
 assert.equal(proposedText(snapshot,option,text+' Changed.'),null);
 assert.equal(proposedText(snapshot,{...option,span:{start:0,end:7}},text),null);
});
test('whole paragraph and selection are explicit; stale recovery cannot apply suggestions',()=>{
 const s=discussionScope('A sentence. Another sentence.',0,11,true);
 assert.equal(s.scope,'Whole paragraph');assert.equal(s.selected,'A sentence. Another sentence.');
 assert.equal(discussionScope(s.text,0,11).selected,'A sentence.');
 assert.equal(proposedText(null,{},s.text),null);
});
test('reopened advice recovers an exact paragraph and Python Unicode selection offsets',()=>{
 const text='📌 A first sentence. A second sentence.',start=[...text].join('').indexOf('A second')-1;
 const job={original_text:text,text:'A second sentence.',selection_start:start,selection_end:[...text].length};
 const snapshot=recoverDiscussion(job,text);
 assert.equal(snapshot.selected,job.text);assert.equal(snapshot.start,text.indexOf('A second'));
 const option={quote:'second',replacement:'clearer',span:{start:2,end:8}};
 assert.equal(proposedText(snapshot,option,text).text,'📌 A first sentence. A clearer sentence.');
 assert.equal(recoverDiscussion(job,text+' New work.'),null);
 assert.equal(recoverDiscussion({...job,selection_start:start-1},text),null);
 assert.equal(recoverDiscussion({...job,selection_end:9999},text),null);
});
test('legacy advice applies only when the complete discussed text matches',()=>{
 assert.equal(recoverDiscussion({text:'Exact paragraph.'},'Exact paragraph.').selected,'Exact paragraph.');
 assert.equal(recoverDiscussion({text:'A selection.'},'Before. A selection. After.'),null);
 assert.equal(proposedText(discussionScope('Text'),{quote:'Text',replacement:'Edit'},'Text'),null);
});
function option(text,quote,replacement){const start=text.indexOf(quote);return {quote,replacement,span:{start,end:start+quote.length}}}
test('three separate suggestions can be applied in any order, preserving earlier edits',()=>{
 const text='We have to check the data. Results are very useful. This is due to noise.';
 const options=[option(text,'have to','need to'),option(text,'very useful','informative'),option(text,'due to','caused by')],snapshot=discussionScope(text);
 for(const order of [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]]){
  let current=text;const used=[];
  for(const i of order){
   const next=proposedText(snapshot,options[i],current,options);assert.ok(next);current=next.text;used.push(i);
   for(let j=0;j<options.length;j++){
    const state=proposalState(snapshot,options[j],current,options);
    assert.equal(state.applied===true,used.includes(j));assert.equal(Boolean(state.next),!used.includes(j));
   }
  }
  assert.equal(current,'We need to check the data. Results are informative. This is caused by noise.');
 }
 assert.equal(snapshot.text,text);
});
test('length changes and Unicode keep a selected occurrence anchored inside its scope',()=>{
 const text='📌 We have to check. They have to wait. Results are very useful. Another have to stays.';
 const start=text.indexOf('They'),end=text.indexOf(' Another'),snapshot=discussionScope(text,start,end);
 const options=[option(snapshot.selected,'They','Those researchers 🧑‍🔬'),option(snapshot.selected,'have to','must'),option(snapshot.selected,'very useful','informative')];
 let current=proposedText(snapshot,options[0],text,options).text;
 current=proposedText(snapshot,options[2],current,options).text;
 const next=proposedText(snapshot,options[1],current,options);
 assert.equal(next.text,'📌 We have to check. Those researchers 🧑‍🔬 must wait. Results are informative. Another have to stays.');
 assert.equal(next.text.slice(next.start,next.end),'must');
});
test('overlapping alternatives are blocked while a separate passage remains available',()=>{
 const text='We have to check. They wait.',snapshot=discussionScope(text);
 const options=[option(text,'have to','must'),option(text,'We have to check.','We need to check.'),option(text,'They wait.','They pause.')];
 const current=proposedText(snapshot,options[0],text,options).text;
 assert.match(proposalState(snapshot,options[1],current,options).notice,/overlaps/);
 assert.equal(proposedText(snapshot,options[1],current,options),null);
 assert.equal(proposedText(snapshot,options[2],current,options).text,'We must check. They pause.');
 assert.ok(proposedText(snapshot,options[1],text,options)); // Undo restores availability.
});
test('reopening the question recognises earlier accepted edits, including a selected passage',()=>{
 const original='📌 Before. We have to check. Results are very useful. After.',start=original.indexOf('We'),end=original.indexOf(' After.');
 const snapshot=discussionScope(original,start,end),options=[option(snapshot.selected,'have to','must'),option(snapshot.selected,'very useful','informative')];
 const job={original_text:original,text:snapshot.selected,selection_start:[...original.slice(0,start)].length,selection_end:[...original.slice(0,end)].length,result:{suggestions:options}};
 const changed=proposedText(snapshot,options[0],original,options).text,recovered=recoverDiscussion(job,changed);
 assert.deepEqual(recovered,snapshot);
 assert.equal(proposedText(recovered,options[1],changed,options).text,'📌 Before. We must check. Results are informative. After.');
 assert.equal(recoverDiscussion(job,changed+' My newer sentence.'),null);
});
test('unrecognised manual changes and a moved quotation are never overwritten',()=>{
 const text='We have to check. They wait.',snapshot=discussionScope(text);
 const options=[option(text,'have to','must'),option(text,'They wait.','They pause.')];
 const first=proposedText(snapshot,options[0],text,options).text;
 for(const changed of [first+' New work.',first.replace('wait','rest'),'We must check. New place: They wait.']){
  assert.equal(proposedText(snapshot,options[1],changed,options),null);
  assert.match(proposalState(snapshot,options[1],changed,options).notice,/newer edits will not be overwritten/);
 }
});
test('an optional check arriving later does not disable remaining suggestions',()=>{
 const text='We have to check. They wait.',snapshot=discussionScope(text),options=[option(text,'have to','must'),option(text,'They wait.','They pause.')];
 const current=proposedText(snapshot,options[0],text,options).text;
 const checked=options.map(o=>({...o,check:{status:'needs_attention',apply_allowed:false}}));
 const state=proposalState(snapshot,checked[1],current,checked);
 assert.equal(state.next.text,'We must check. They pause.');assert.match(state.notice,/Earlier suggested edits will be kept/);
});
