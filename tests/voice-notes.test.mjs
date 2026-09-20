import test from 'node:test';
import assert from 'node:assert/strict';
import {voiceInsertion,undoVoiceInsertion,VoiceRecoveryStore,VoiceCapture,uploadVoiceClip,createVoiceNotesUI,finishVoiceNotes,orderedVoiceMerge,moveVoiceClip} from '../dist/voice-notes.js';

const clip=(id,duration=20,extra={})=>({id,title:'Clip '+id,paper_id:'paper',section_id:'section',duration_seconds:duration,...extra});
test('merge preserves the explicit playback order and does not mutate original clips or selection',()=>{
 const notes=[clip('a'),clip('b',30),clip('c',10)],ids=['c','a','b'],before=JSON.stringify(notes);
 const plan=orderedVoiceMerge(ids,notes,{paperId:'paper',sectionId:'section'});
 assert.deepEqual(plan.note_ids,['c','a','b']);assert.deepEqual(plan.notes.map(n=>n.id),ids);assert.equal(plan.seconds,60);assert.equal(JSON.stringify(notes),before);
 const moved=moveVoiceClip(ids,'a',-1);assert.deepEqual(moved,['a','c','b']);assert.deepEqual(ids,['c','a','b']);
 assert.deepEqual(moveVoiceClip(moved,'a',-1),moved);assert.deepEqual(moveVoiceClip(moved,'b',1),moved);assert.deepEqual(moveVoiceClip(moved,'missing',1),moved);assert.deepEqual(moveVoiceClip(moved,'c',10),moved);
});

test('merge rejects incomplete, repeated, missing or cross-section sources and recordings in trash',()=>{
 const notes=[clip('a'),clip('b'),clip('trash',20,{trashed:true}),clip('other',20,{section_id:'other'})];
 assert.match(orderedVoiceMerge(['a'],notes).error,/2 and 10/);
 assert.match(orderedVoiceMerge(Array(11).fill('a'),notes).error,/2 and 10/);
 assert.match(orderedVoiceMerge(['a','a'],notes).error,/only once/);
 assert.match(orderedVoiceMerge(['a','missing'],notes).error,/no longer available/);
 assert.match(orderedVoiceMerge(['a','trash'],notes).error,/Restore/);
 assert.match(orderedVoiceMerge(['a','other'],notes).error,/same paper and section/);
 assert.match(orderedVoiceMerge(['a','b'],notes,{paperId:'another-paper'}).error,/same paper and section/);
});

test('merge bounds known total duration while permitting saved audio with transcription still running',()=>{
 const notes=[clip('a',300,{status:'transcribing'}),clip('b',300,{status:'queued'}),clip('c',301)];
 assert.equal(orderedVoiceMerge(['a','b'],notes).seconds,600);
 assert.match(orderedVoiceMerge(['a','c'],notes).error,/10 minutes/);
 const missing=orderedVoiceMerge(['a','x'],[...notes,{id:'x',paper_id:'paper',section_id:'section'}]);assert.equal(missing.durationKnown,false);assert.equal(missing.seconds,300);
});

test('Keep notes stays open on a failed or conflicting save, while ordinary close can leave with recovery',async()=>{
 let closed=0;
 const close=async()=>{closed++;};
 assert.equal(await finishVoiceNotes({save:async()=>false,close,requireSaved:true}),false);
 assert.equal(closed,0);
 assert.equal(await finishVoiceNotes({save:async()=>true,close,requireSaved:true}),true);
 assert.equal(closed,1);
 assert.equal(await finishVoiceNotes({save:async()=>false,close}),true);
 assert.equal(closed,2);
 await assert.rejects(finishVoiceNotes({save:async()=>{throw new Error('Connection failed');},close,requireSaved:true}),/Connection failed/);
 assert.equal(closed,2);
});

test('only explicitly selected spoken words enter the draft at the captured cursor',()=>{
 const draft='First. Last.',transcript='Do not copy this. My own spoken idea. Or this.';
 const start=transcript.indexOf('My own'),end=transcript.indexOf(' Or this.');
 const result=voiceInsertion({text:draft,cursor:7},draft,transcript,start,end);
 assert.equal(result.text,'First. My own spoken idea. Last.');assert.equal(result.edit.before,draft);
 assert.doesNotMatch(result.text,/Do not copy|Or this/);
 assert.equal(undoVoiceInsertion(result.edit,result.text).text,draft);
});

test('stale snapshots, missing selections and length overruns never replace draft text',()=>{
 assert.match(voiceInsertion({text:'Before',cursor:3},'After','Some notes',0,4).error,/draft changed/);
 assert.match(voiceInsertion({text:'Before',cursor:9},'Before','Some notes',0,4).error,/cursor/);
 assert.match(voiceInsertion({text:'Before',cursor:3},'Before','Some notes',4,4).error,/Select/);
 assert.match(voiceInsertion({text:'Before',cursor:3},'Before','   ',0,3).error,/Select/);
 const big='a'.repeat(39999);assert.match(voiceInsertion({text:big,cursor:big.length},big,'more',0,4).error,/limit/);
});

test('undo removes the exact insertion and preserves an unrelated later revision',()=>{
 const before='Old opening. '+('Unchanged context. '.repeat(6))+' Finish.';
 const r=voiceInsertion({text:before,cursor:before.indexOf(' Finish.')},before,'My recorded thought.',0,20);
 const changed=r.text.replace('Old opening.','An improved opening.');
 assert.equal(undoVoiceInsertion(r.edit,changed).text,before.replace('Old opening.','An improved opening.'));
 assert.match(undoVoiceInsertion(r.edit,changed.replace('recorded','rewritten')).error,/changed/);
 assert.match(undoVoiceInsertion(r.edit,changed+' '+r.edit.inserted).error,/changed/);
});

function microphone(){let stopped=0;return {stream:{getTracks:()=>[{stop:()=>{stopped++;}}]},stopped:()=>stopped};}
class FakeRecorder {
 static isTypeSupported(type){return type==='audio/webm;codecs=opus';}
 constructor(stream,options){this.mimeType=options?.mimeType||'audio/webm';this.state='inactive';FakeRecorder.last=this;}
 start(){this.state='recording';}
 pause(){this.state='paused';}
 resume(){this.state='recording';}
 chunk(value){this.ondataavailable?.({data:new Blob([value],{type:this.mimeType})});}
 stop(){this.state='inactive';queueMicrotask(()=>{this.chunk('last');this.onstop?.();});}
}

test('recording persists cumulative audio chunks, excludes pauses from duration and releases microphone',async()=>{
 const mic=microphone(),saved=[],states=[];let now=0;
 const recording=new VoiceCapture({mediaDevices:{getUserMedia:async()=>mic.stream},Recorder:FakeRecorder,now:()=>now,onChunk:async(blob)=>saved.push(await blob.text()),onState:s=>states.push(s)});
 await recording.start();FakeRecorder.last.chunk('first');now=2000;recording.pause();now=8000;assert.equal(recording.duration(),2);
 recording.resume();now=9000;const final=await recording.stop();
 assert.equal(recording.duration(),3);assert.equal(await final.text(),'firstlast');assert.deepEqual(saved,['first','firstlast']);assert.equal(mic.stopped(),1);assert.deepEqual(states,['starting','recording','paused','recording','stopping','stopped']);
});

test('permission errors are actionable and constructing the UI never starts the microphone',async()=>{
 const denied=new VoiceCapture({mediaDevices:{getUserMedia:async()=>{const e=new Error('denied');e.name='NotAllowedError';throw e;}},Recorder:FakeRecorder});
 await assert.rejects(denied.start(),/permission was not granted/);assert.equal(denied.state,'idle');
 const ui=createVoiceNotesUI({api:async()=>{throw new Error('Do not call API before opening');},esc:String});assert.equal(ui.hasRecording(),null);
});

test('navigation while permission is pending cancels capture and releases a later acquired stream',async()=>{
 const mic=microphone();let allow;
 const recording=new VoiceCapture({mediaDevices:{getUserMedia:()=>new Promise(resolve=>allow=resolve)},Recorder:FakeRecorder});
 const starting=recording.start();await recording.stop();allow(mic.stream);assert.equal(await starting,false);assert.equal(mic.stopped(),1);assert.equal(recording.recorder,null);
});

test('recorder construction failure releases the microphone and runtime errors preserve captured audio',async()=>{
 const mic=microphone();class BadRecorder {constructor(){throw new Error('Unsupported encoder');}}
 const bad=new VoiceCapture({mediaDevices:{getUserMedia:async()=>mic.stream},Recorder:BadRecorder});await assert.rejects(bad.start(),/Unsupported encoder/);assert.equal(mic.stopped(),1);
 const mic2=microphone(),recording=new VoiceCapture({mediaDevices:{getUserMedia:async()=>mic2.stream},Recorder:FakeRecorder});await recording.start();FakeRecorder.last.chunk('kept');FakeRecorder.last.onerror({error:{message:'Input disconnected'}});const blob=await recording.stop();assert.equal(await blob.text(),'keptlast');assert.equal(recording.runtimeError,'Input disconnected');assert.equal(mic2.stopped(),1);
});

test('recovery storage failure retains audio in the current tab and scopes recovery to its section',async()=>{
 const store=new VoiceRecoveryStore(null),blob=new Blob(['audio']);
 assert.equal(await store.put({key:'one',paper_id:'paper',section_id:'section',blob}),false);assert.match(store.error,/unavailable/);
 assert.equal((await store.list('paper','section'))[0].blob,blob);assert.equal((await store.list('other','section')).length,0);
 await store.remove('one');assert.equal((await store.list('paper','section')).length,0);
});

test('upload stores audio before any transcription request and retries authentication with the same key',async()=>{
 const calls=[],tokens=['first','second'];let n=0;
 const result=await uploadVoiceClip({api:async()=>({token:tokens.shift()}),path:'/workspace/papers/p/voice-notes',clip:{key:'stable-upload',blob:new Blob(['audio'],{type:'audio/webm'}),filename:'clip.webm',section_id:'s',idea_id:'idea',language:'auto'},fetcher:async(url,options)=>{calls.push({url,options});n++;return n===1?{status:403}:{status:200,ok:true,json:async()=>({id:'saved'})};}});
 assert.equal(result.id,'saved');assert.equal(calls.length,2);assert.equal(calls[0].options.body.get('transcribe'),'false');assert.equal(calls[1].options.body.get('request_key'),'stable-upload');assert.equal(calls[1].options.headers['X-AWL-Token'],'second');assert.equal(calls[0].options.body.get('section_id'),'s');assert.equal(calls[0].options.body.get('file').name,'clip.webm');
});

test('upload errors are reported rather than pretending audio has been saved',async()=>{
 await assert.rejects(uploadVoiceClip({api:async()=>({token:'x'}),path:'/notes',clip:{key:'same',blob:new Blob(['x'])},fetcher:async()=>({status:422,ok:false,json:async()=>({detail:'The audio decoder is unavailable.'})})}),/decoder/);
});
