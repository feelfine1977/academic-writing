const enc=encodeURIComponent;
const activeStates=new Set(['queued','transcribing']);
const MAX_BYTES=40000000,MAX_SECONDS=600;
const labelStatus={saved:'Audio saved · ready to transcribe',queued:'Waiting for local transcription',transcribing:'Transcribing on this computer',complete:'Transcript ready',failed:'Transcription needs attention',cancelled:'Transcription cancelled'};
const uid=()=>globalThis.crypto?.randomUUID?.()||`voice-${Date.now()}-${Math.random().toString(16).slice(2)}`;
const time=seconds=>`${Math.floor(Math.max(0,seconds)/60)}:${String(Math.floor(Math.max(0,seconds)%60)).padStart(2,'0')}`;
const text=value=>typeof value==='string'?value:'';

export async function finishVoiceNotes({save,close,requireSaved=false}){
 const saved=await save();
 if(requireSaved&&!saved)return false;
 await close();return true;
}

export function orderedVoiceMerge(ids,notes,{paperId,sectionId,maxSeconds=MAX_SECONDS}={}){
 if(!Array.isArray(ids)||ids.length<2||ids.length>10)return {error:'Choose between 2 and 10 saved recordings to merge.'};
 if(new Set(ids).size!==ids.length)return {error:'Each recording can appear only once in a merge.'};
 const ordered=ids.map(id=>notes.find(note=>note.id===id));
 if(ordered.some(note=>!note))return {error:'A selected recording is no longer available. Refresh and choose again.'};
 if(ordered.some(note=>note.trashed))return {error:'Restore recordings from trash before including them in a merge.'};
 if(ordered.some(note=>note.paper_id!==(paperId||ordered[0].paper_id)||note.section_id!==(sectionId||ordered[0].section_id)))return {error:'Choose recordings from the same paper and section.'};
 const duration=ordered.reduce((sum,note)=>sum+(Number.isFinite(note.duration_seconds)?note.duration_seconds:0),0);
 if(duration>maxSeconds)return {error:'The combined recording must be no longer than 10 minutes. Choose fewer or shorter clips.'};
 return {notes:ordered,seconds:duration,durationKnown:ordered.every(note=>Number.isFinite(note.duration_seconds)),note_ids:[...ids]};
}

export function moveVoiceClip(ids,id,direction){
 const next=[...ids],index=next.indexOf(id),target=index+direction;
 if(index<0||![1,-1].includes(direction)||target<0||target>=next.length)return next;
 [next[index],next[target]]=[next[target],next[index]];return next;
}

export function voiceInsertion(anchor,current,transcript,start,end){
 if(!anchor||typeof anchor.text!=='string'||anchor.text!==current)return {error:'Your draft changed after you opened these notes. Close and reopen Speak my idea to choose the current insertion point.'};
 if(!Number.isInteger(anchor.cursor)||anchor.cursor<0||anchor.cursor>current.length)return {error:'Place the cursor in your draft, then open Speak my idea again.'};
 if(typeof transcript!=='string'||!Number.isInteger(start)||!Number.isInteger(end)||start<0||end>transcript.length||end<=start)return {error:'Select the words you want to insert in your editable spoken notes first.'};
 const chosen=transcript.slice(start,end);if(!chosen.trim())return {error:'Select some words in your spoken notes first.'};
 const before=current.slice(0,anchor.cursor),after=current.slice(anchor.cursor);
 const inserted=(before&&!/\s$/u.test(before)?' ':'')+chosen+(after&&!/^\s/u.test(after)?' ':'');
 if(current.length+inserted.length>40000)return {error:'This would exceed the section draft limit. Select a shorter passage.'};
 const value=before+inserted+after;
 return {text:value,edit:{before:current,after:value,start:anchor.cursor,inserted,left:before.slice(-40),right:after.slice(0,40)}};
}

export function undoVoiceInsertion(edit,current){
 if(!edit||typeof current!=='string'||!edit.inserted)return {error:'There is no spoken-text insertion to undo.'};
 if(current===edit.after)return {text:edit.before};
 const start=current.indexOf(edit.inserted);
 if(start<0||current.indexOf(edit.inserted,start+1)>=0||current.slice(Math.max(0,start-edit.left.length),start)!==edit.left||current.slice(start+edit.inserted.length,start+edit.inserted.length+edit.right.length)!==edit.right)return {error:'The inserted words or their immediate context changed. Keep your later edits and remove the words manually if needed.'};
 return {text:current.slice(0,start)+current.slice(start+edit.inserted.length)};
}

// Every chunk is recoverable before upload. In-memory fallback remains available
// in this tab if browser storage is unavailable; the UI makes that limit visible.
export class VoiceRecoveryStore {
 constructor(indexedDB=globalThis.indexedDB){this.indexedDB=indexedDB;this.memory=new Map();this.error='';this.pending=null;}
 async db(){
  if(!this.indexedDB)throw new Error('Browser recovery storage is unavailable.');
  if(!this.pending)this.pending=new Promise((resolve,reject)=>{const request=this.indexedDB.open('awl-voice-recovery',1);request.onupgradeneeded=()=>{if(!request.result.objectStoreNames.contains('clips'))request.result.createObjectStore('clips',{keyPath:'key'});};request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error||new Error('Browser recovery could not open.'));request.onblocked=()=>reject(new Error('Another tab blocked voice recovery storage.'));});
  return this.pending;
 }
 async transaction(mode,work){const db=await this.db();return new Promise((resolve,reject)=>{const tx=db.transaction('clips',mode),req=work(tx.objectStore('clips'));let value;req.onsuccess=()=>{value=req.result};tx.oncomplete=()=>resolve(value);tx.onerror=()=>reject(tx.error||req.error||new Error('Browser recovery failed.'));tx.onabort=()=>reject(tx.error||new Error('Browser recovery was interrupted.'));});}
 async put(record){this.memory.set(record.key,record);try{await this.transaction('readwrite',store=>store.put(record));this.error='';return true;}catch(e){this.error=e.message;return false;}}
 async list(paper,section){let rows=[];try{rows=await this.transaction('readonly',store=>store.getAll());this.error='';}catch(e){this.error=e.message;}const merged=new Map(rows.map(row=>[row.key,row]));for(const [key,row] of this.memory)merged.set(key,row);return [...merged.values()].filter(row=>row.paper_id===paper&&row.section_id===section);}
 async remove(key){this.memory.delete(key);try{await this.transaction('readwrite',store=>store.delete(key));return true;}catch(e){this.error=e.message;return false;}}
}

export class VoiceCapture {
 constructor({mediaDevices=globalThis.navigator?.mediaDevices,Recorder=globalThis.MediaRecorder,onChunk=async()=>{},onState=()=>{},now=()=>performance.now()}={}){Object.assign(this,{mediaDevices,Recorder,onChunk,onState,now});this.state='idle';this.parts=[];this.elapsed=0;this.started=0;this.stream=null;this.recorder=null;this.chain=Promise.resolve();this.cancelled=false;this.stopping=null;}
 duration(){return (this.elapsed+(this.state==='recording'?this.now()-this.started:0))/1000;}
 update(state){this.state=state;this.onState(state);}
 release(){this.stream?.getTracks().forEach(track=>track.stop());this.stream=null;}
 async start(){
  if(!this.mediaDevices?.getUserMedia||!this.Recorder)throw new Error('Microphone recording is unavailable here. Use a supported browser on this computer, or import an audio file.');
  this.update('starting');
  try{
   this.stream=await this.mediaDevices.getUserMedia({audio:true});if(this.cancelled){this.release();this.update('idle');return false;}
   const mime=['audio/webm;codecs=opus','audio/mp4','audio/ogg;codecs=opus','audio/webm'].find(value=>this.Recorder.isTypeSupported?.(value));
   this.recorder=new this.Recorder(this.stream,mime?{mimeType:mime}:undefined);
   this.recorder.ondataavailable=event=>{if(event.data?.size){this.parts.push(event.data);const blob=new Blob(this.parts,{type:this.recorder.mimeType||event.data.type||'audio/webm'});this.chain=this.chain.then(()=>this.onChunk(blob,this.duration())).catch(error=>{this.chunkError=error;});}};
   this.recorder.onerror=event=>{this.runtimeError=event.error?.message||'The microphone recording stopped unexpectedly.';this.stop().catch(()=>{});};
   this.recorder.start(1000);this.started=this.now();this.update('recording');return true;
  }catch(error){this.release();this.update('idle');throw new Error(error.name==='NotAllowedError'?'Microphone permission was not granted. Allow access in your browser or import an audio file.':error.message||'The microphone could not start.');}
 }
 pause(){if(this.state!=='recording')return;this.recorder.pause();this.elapsed+=this.now()-this.started;this.update('paused');}
 resume(){if(this.state!=='paused')return;this.recorder.resume();this.started=this.now();this.update('recording');}
 async stop(){
  if(this.stopping)return this.stopping;
  if(this.state==='starting'){this.cancelled=true;return null;}
  if(!this.recorder)return null;
  if(this.state==='recording')this.elapsed+=this.now()-this.started;
  this.update('stopping');
  this.stopping=(async()=>{
   await new Promise(resolve=>{let done=false;const finish=()=>{if(done)return;done=true;clearTimeout(timer);resolve();};const timer=setTimeout(finish,3000);this.recorder.onstop=finish;if(this.recorder.state==='inactive')finish();else{try{this.recorder.stop();}catch{finish();}}this.release();});
   await this.chain;this.update('stopped');return new Blob(this.parts,{type:this.recorder.mimeType||this.parts[0]?.type||'audio/webm'});
  })();return this.stopping;
 }
}

export async function uploadVoiceClip({api,fetcher=globalThis.fetch,path,clip}){
 const body=new FormData();body.append('file',clip.blob,clip.filename||'spoken-idea.webm');
 for(const name of ['section_id','idea_id','title','language'])body.append(name,clip[name]||'');body.append('request_key',clip.key);body.append('transcribe','false');
 const bootstrap=await api('/bootstrap');
 const send=token=>fetcher('/api'+path,{method:'POST',headers:{'X-AWL-Token':token||''},body});
 let response=await send(bootstrap.token);if(response.status===403)response=await send((await api('/bootstrap')).token);
 let result;try{result=await response.json();}catch{throw new Error('Audio could not be saved. Your recovery copy is kept in this browser.');}
 if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'Audio could not be saved. Try again; your recovery copy is kept.');return result;
}

export function createVoiceNotesUI({api,esc,toast=()=>{},fetcher=globalThis.fetch,recovery=new VoiceRecoveryStore()}={}){
 let view=null,capture=null,clip=null,uploading=new Set(),notes=[],selected=null,statusInfo=null,dialog=null,pollTimer=null,clockTimer=null,saveTimer=null,saveChain=Promise.resolve(),returnFocus=null,anchor=null,lastInsertion=null,showTrashed=false,mergeIds=[],mergeTitle='Merged spoken idea',mergeBusy=false,mergeRequest=null;
 const path=scope=>`/workspace/papers/${enc(scope.paperId)}/voice-notes`;
 const $=selector=>dialog?.querySelector(selector);
 const same=scope=>view&&scope.paperId===view.paperId&&scope.sectionId===view.sectionId;
 const noteURL=(scope,note)=>path(scope)+'/'+enc(note.id);
 const busy=()=>capture&&['starting','recording','paused','stopping'].includes(capture.state);
 function message(value,error=false){if(!dialog?.open)return;$('#voice-notice').textContent=value;$('#voice-notice').classList.toggle('error',error);}
 function statusMarkup(){const ready=statusInfo?.ready,canSave=statusInfo?.decoder_ready;return `<strong>${ready?'Local transcription is ready':canSave?'Audio can be saved; transcription needs setup':'Local audio setup is needed'}</strong><p>${esc(statusInfo?.message||'Checking local transcription setup…')}</p>${statusInfo&&!ready?`<p>Engine: ${statusInfo.engine_ready?'ready':'not available'} · Model: ${statusInfo.model_ready?'ready':'not available'} · Audio decoder: ${canSave?'ready':'not available'}</p><p>${canSave?'Install or configure the local Whisper engine and model to transcribe saved audio.':'Install or configure FFmpeg to save recordings into the paper. Until then, recordings remain in browser recovery and can be downloaded.'} In your Writing Lab app folder, run <strong>Set up voice on Mac.command</strong> on Mac or <strong>Set up voice on Windows.cmd</strong> on Windows. Then select “Check setup again”.</p>`:''}`;}
 function controls(){if(!dialog?.open)return;const state=capture?.state||'idle',recording=state==='recording',paused=state==='paused';$('#voice-record').disabled=busy();$('#voice-import').disabled=busy();$('#voice-language').disabled=busy();$('#voice-pause').hidden=!(recording||paused);$('#voice-pause').textContent=paused?'Resume':'Pause';$('#voice-stop').hidden=!(recording||paused);$('#voice-recording').hidden=!busy();$('#voice-recording').dataset.state=state;$('#voice-recording-label').textContent=paused?'Paused · microphone connected':state==='starting'?'Waiting for microphone permission':state==='stopping'?'Saving recording…':'Recording · microphone on';$('#voice-duration').textContent=time(capture?.duration()||0);}
 function drawHistory(){if(!dialog?.open)return;const rows=notes.filter(note=>showTrashed||!note.trashed);$('#voice-history').innerHTML=rows.map(note=>`<button class="voice-history-item ${selected?.id===note.id?'selected':''} ${note.trashed?'voice-trashed':''}" data-voice-note="${esc(note.id)}"><strong>${esc(note.title||'Spoken idea')}</strong><span>${note.trashed?'In trash · can be restored':esc(labelStatus[note.status]||note.status)}${note.idea_id?' · '+esc(note.idea_id):''}</span><small>${esc(new Date(note.created).toLocaleString())}</small></button>`).join('')||'<p>No recordings in this view.</p>';$('#voice-history').querySelectorAll('[data-voice-note]').forEach(button=>button.onclick=()=>choose(notes.find(note=>note.id===button.dataset.voiceNote)));drawManagement();}
 function drawManagement(){
  if(!dialog?.open||!$('#voice-management'))return;
  const active=notes.filter(note=>!note.trashed),planned=orderedVoiceMerge(mergeIds,notes,view||{});
  $('#voice-management').innerHTML=`<p>Merge 2–10 recordings from this section into a new recording. Your originals and their notes stay unchanged. The result must fit within 10 minutes and 40 MB.</p><div class="voice-merge-picker">${active.map(note=>`<label><input type="checkbox" data-voice-select="${esc(note.id)}" ${mergeIds.includes(note.id)?'checked':''} ${mergeBusy?'disabled':''}><span>${esc(note.title||'Spoken idea')} <small>${time(note.duration_seconds||0)}</small></span></label>`).join('')||'<p>Save at least two recordings to merge them.</p>'}</div><h4>Play in this order</h4><ol class="voice-merge-order">${mergeIds.map((id,i)=>{const note=notes.find(n=>n.id===id);return `<li><span>${esc(note?.title||'Unavailable recording')}</span><button class="btn quiet" data-voice-up="${esc(id)}" aria-label="Move ${esc(note?.title||'recording')} earlier" ${i===0||mergeBusy?'disabled':''}>↑ Earlier</button><button class="btn quiet" data-voice-down="${esc(id)}" aria-label="Move ${esc(note?.title||'recording')} later" ${i===mergeIds.length-1||mergeBusy?'disabled':''}>↓ Later</button></li>`;}).join('')||'<li>Select recordings above, then adjust their order here.</li>'}</ol><label class="field">Name of the merged recording<input id="voice-merge-title" maxlength="160" value="${esc(mergeTitle)}" ${mergeBusy?'disabled':''}></label><p class="tiny">${esc(planned.error||`${mergeIds.length} recordings · about ${time(planned.seconds)}. A fresh transcript will follow when local transcription is available.`)}</p><button class="btn secondary" id="voice-merge" ${planned.error||mergeBusy?'disabled':''}>${mergeBusy?'Merging saved audio…':'Merge into a new recording'}</button><p class="tiny">Merge combines the audio in this order. It does not join or rewrite your edited notes, and it does not delete any source recordings.</p>`;
  $('#voice-management').querySelectorAll('[data-voice-select]').forEach(input=>input.onchange=()=>{const id=input.dataset.voiceSelect;if(input.checked&&mergeIds.length>=10){input.checked=false;message('Choose up to 10 recordings per merge.',true);return;}mergeIds=input.checked?[...mergeIds,id]:mergeIds.filter(value=>value!==id);mergeRequest=null;drawManagement();});
  for(const [selector,direction,key] of [['[data-voice-up]',-1,'voiceUp'],['[data-voice-down]',1,'voiceDown']])$('#voice-management').querySelectorAll(selector).forEach(button=>button.onclick=()=>{mergeIds=moveVoiceClip(mergeIds,button.dataset[key],direction);mergeRequest=null;drawManagement();});
  $('#voice-merge-title').oninput=e=>{mergeTitle=e.target.value;mergeRequest=null;};$('#voice-merge').onclick=()=>mergeRecordings();
 }
 async function mergeRecordings(){
  const scope=view,plan=orderedVoiceMerge(mergeIds,notes,scope||{});if(!scope||mergeBusy)return;if(plan.error){message(plan.error,true);return;}if(busy()){message('Stop and save the current recording before merging clips.',true);return;}
  clearTimeout(saveTimer);if(!await saveText(scope,selected)||!same(scope))return;
  const title=mergeTitle.trim()||'Merged spoken idea',language=$('#voice-language').value,signature=JSON.stringify([plan.note_ids,title,language]);
  if(mergeRequest?.signature!==signature)mergeRequest={signature,key:uid()};const requestKey=mergeRequest.key;mergeBusy=true;drawManagement();
  try{const result=await api(path(scope)+'/merge',{note_ids:plan.note_ids,title,language,request_key:requestKey});if(same(scope)){notes=[result,...notes.filter(note=>note.id!==result.id)];selected=result;mergeIds=[];mergeRequest=null;editor();drawHistory();message('Merged audio saved as a new recording. Your originals and notes are kept.');}if(statusInfo?.ready)await transcribe(scope,result,language);}
  catch(e){if(same(scope))message('The recordings were not deleted. '+e.message,true);}
  finally{mergeBusy=false;if(same(scope))drawManagement();}
 }
 async function trashOrRestore(note,restore=false){
  const scope=view;if(!scope||!note)return;clearTimeout(saveTimer);const recovered=restore&&selected?.id===note.id&&selected._dirty?{...selected}:null;
  if(recovered)await recoverText(scope,recovered);else if(!await saveText(scope,selected))return;if(!same(scope))return;
  try{const result=await api(noteURL(scope,note)+(restore?'/restore':'/trash'),{});if(!same(scope))return;showTrashed=!restore;$('#voice-show-trashed').checked=showTrashed;mergeIds=mergeIds.filter(id=>id!==note.id);selected=recovered?{...result,corrected_text:recovered.corrected_text,ideas_text:recovered.ideas_text,_dirty:true,_conflict:true,_vault_text:result.corrected_text,_vault_ideas:result.ideas_text}:result;updateNote(scope,result);if(recovered)editor();message(restore?'Recording restored. Your audio and notes are available again.':'Recording moved to trash. Open it here and select Restore recording to bring it back.');}
  catch(e){if(same(scope))message('Your recording is kept. '+e.message,true);}
 }
 function audioURL(note){const expected='/api'+path(view)+'/'+enc(note.id)+'/audio';return typeof note.audio_url==='string'&&note.audio_url===expected?note.audio_url:expected;}
 function editor(){if(!dialog?.open)return;const note=selected;$('#voice-editor').hidden=!note;if(!note)return;
  $('#voice-editor').innerHTML=`<h3>${esc(note.title||'My spoken idea')}</h3><p class="voice-note-state">${esc(labelStatus[note.status]||note.status)}</p><p class="tiny">${esc(note.sync_message||'Saved with this paper. Spoken notes are separate from manuscript prose.')}</p>${note.error?`<p class="voice-error">${esc(note.error)}</p>`:''}<audio id="voice-audio" controls preload="metadata" src="${esc(audioURL(note))}"></audio><div class="actions"><button class="btn secondary" id="voice-transcribe" ${activeStates.has(note.status)||!statusInfo?.ready?'disabled':''}>${note.original_text?'Transcribe audio again':'Transcribe saved audio'}</button><button class="btn quiet" id="voice-cancel" ${activeStates.has(note.status)?'':'hidden'}>Cancel transcription</button></div><label class="field">My spoken notes · editable<textarea id="voice-corrected" rows="8" maxlength="40000" placeholder="The transcript appears here when ready. You can correct recognition mistakes and organise your own words.">${esc(note.corrected_text||'')}</textarea></label><label class="field">My extra ideas or reminders<textarea id="voice-ideas" rows="3" maxlength="20000" placeholder="What I want to keep or develop when writing…">${esc(note.ideas_text||'')}</textarea></label><p class="tiny" id="voice-note-save">These are your notes, not tutor guidance or the manuscript.</p><div class="actions"><button class="btn" id="voice-keep">Keep notes & write myself</button><button class="btn secondary" id="voice-insert">Insert selected words at my draft cursor</button><button class="btn quiet" id="voice-undo" ${lastInsertion?'':'hidden'}>Undo spoken-text insertion</button></div><p class="tiny">To insert text, select only the words you want in “My spoken notes”. Nothing is inserted automatically.</p><details><summary>Original transcript and audio timestamps</summary><p class="tiny">Recognition can be wrong. The original transcript stays unchanged when you edit your notes.</p><pre class="voice-original">${esc(note.original_text||'No original transcript yet.')}</pre><div class="voice-segments">${(note.segments||[]).filter(s=>Number.isFinite(s.start)&&s.start>=0).map((segment,i)=>`<button class="voice-segment" data-voice-time="${Number(segment.start)}"><span>${time(segment.start)}</span>${esc(segment.text||'')}</button>`).join('')}</div></details>`;
  if(note._conflict){const warning=document.createElement('div');warning.className='voice-error';warning.innerHTML=`<strong>Recovered edits need comparison</strong><p>Your recovered notes are in the editor. The saved notes below changed while you were away.</p><pre class="voice-original">${esc(note._vault_text||'No saved spoken notes.')}</pre><pre class="voice-original">${esc(note._vault_ideas||'')}</pre><button class="btn secondary" id="voice-keep-recovery">Save my recovered edits over this saved version</button><button class="btn quiet" id="voice-download-notes">Download recovered notes</button>`;$('#voice-editor').prepend(warning);$('#voice-keep-recovery').onclick=async()=>{if(!confirm('Replace the saved spoken notes with the recovered edits shown here? The original transcript and audio remain unchanged.'))return;selected={...selected,_conflict:false};await saveText(view,selected);editor();};$('#voice-download-notes').onclick=()=>{const blob=new Blob([selected.corrected_text+'\n\n'+selected.ideas_text],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='Recovered spoken notes.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);};}
  if(note.latest_text&&note.latest_text!==note.original_text){const latest=document.createElement('details');latest.className='voice-latest';latest.innerHTML=`<summary>Latest transcription · your edited notes were kept</summary><p class="tiny">A new recognition attempt does not replace your notes or the first transcript. Select and copy any useful words from this version.</p><pre class="voice-original">${esc(note.latest_text)}</pre>`;$('#voice-editor').append(latest);}
  if(Array.isArray(note.merged_from)&&note.merged_from.length){const provenance=document.createElement('details');provenance.className='voice-provenance';provenance.innerHTML=`<summary>Combined from ${note.merged_from.length} recordings</summary><p>The sources remain saved separately. Audio was joined in this order:</p><ol>${note.merged_from.map(source=>`<li>${esc(source.title||'Spoken idea')}</li>`).join('')}</ol>`;$('#voice-editor').append(provenance);}
  const options=document.createElement('details');options.className='voice-record-options';options.innerHTML=`<summary>${note.trashed?'Recording in trash':'Recording options'}</summary><p>${note.trashed?'Your audio and notes are kept. Restore this recording to edit or transcribe it again.':'Move this recording out of your active list. It remains recoverable in the trash.'}</p><button class="btn ${note.trashed?'secondary':'quiet voice-trash-button'}" id="voice-trash-action">${note.trashed?'Restore recording':'Move recording to trash'}</button>`;options.open=!!note.trashed;$('#voice-editor').append(options);$('#voice-trash-action').onclick=()=>trashOrRestore(note,!!note.trashed);
  if(note.trashed){$('#voice-corrected').readOnly=true;$('#voice-ideas').readOnly=true;$('#voice-transcribe').disabled=true;$('#voice-insert').disabled=true;$('#voice-keep').hidden=true;$('#voice-cancel').hidden=true;$('#voice-note-save').textContent='In trash · restore the recording to edit these notes.';}
  for(const [id,field] of [['voice-corrected','corrected_text'],['voice-ideas','ideas_text']])$('#'+id).oninput=event=>{selected={...selected,[field]:event.target.value};selected._dirty=true;recoverText(view,selected);clearTimeout(saveTimer);saveTimer=setTimeout(()=>saveText(view,selected),900);};
  $('#voice-transcribe').onclick=()=>transcribe(view,selected,$('#voice-language').value);$('#voice-cancel').onclick=async()=>{const scope=view,note=selected;try{const result=await api(noteURL(scope,note)+'/cancel',{});updateNote(scope,result);if(same(scope))message('Transcription cancelled. Your audio and notes are kept.');}catch(e){if(same(scope))message(e.message,true);}};
  $('#voice-keep').onclick=async()=>{const scope=view;if(await close({requireSaved:true}))scope?.focusDraft?.();};
  $('#voice-insert').onclick=()=>{const field=$('#voice-corrected'),result=voiceInsertion(anchor,view.getDraft(),field.value,field.selectionStart,field.selectionEnd);if(result.error){message(result.error,true);return;}view.setDraft(result.text);lastInsertion=result.edit;anchor={text:result.text,cursor:result.edit.start+result.edit.inserted.length};$('#voice-undo').hidden=false;message('Only your selected words were inserted. Your spoken notes and original transcript are kept.');};
  $('#voice-undo').onclick=()=>{const result=undoVoiceInsertion(lastInsertion,view.getDraft());if(result.error){message(result.error,true);return;}view.setDraft(result.text);lastInsertion=null;anchor={text:result.text,cursor:Math.min(anchor.cursor,result.text.length)};$('#voice-undo').hidden=true;message('Spoken-text insertion undone. Your other draft edits are kept.');};
  $('#voice-editor').querySelectorAll('[data-voice-time]').forEach(button=>button.onclick=()=>{const player=$('#voice-audio');player.currentTime=Number(button.dataset.voiceTime);player.play().catch(()=>message('Press Play to listen at this timestamp.'));});
 }
 function updateNote(scope,note){if(!same(scope))return;notes=[note,...notes.filter(row=>row.id!==note.id)];if(selected?.id===note.id&&!selected._dirty){selected=note;editor();}drawHistory();schedulePoll();}
 async function recoverText(scope,note){return recovery.put({key:'text-'+note.id,paper_id:scope.paperId,section_id:scope.sectionId,kind:'text',note_id:note.id,base_hash:note.hash,corrected_text:note.corrected_text||'',ideas_text:note.ideas_text||''});}
 async function saveText(scope,note){
  if(!scope||!note?._dirty)return true;
  if(note._conflict){if(same(scope))message('Compare your recovered notes with the saved version before replacing it. Your recovery copy is kept.',true);return false;}
  const sent={corrected_text:note.corrected_text||'',ideas_text:note.ideas_text||''},noteId=note.id;
  saveChain=saveChain.then(async()=>{
   const latest=same(scope)&&selected?.id===noteId?selected:note;
   try{const result=await api(noteURL(scope,note),{base_hash:latest.hash,...sent},'PATCH');
    if(same(scope)&&selected?.id===noteId){const newer=selected.corrected_text!==sent.corrected_text||selected.ideas_text!==sent.ideas_text;selected={...result,...(newer?{corrected_text:selected.corrected_text,ideas_text:selected.ideas_text,_dirty:true}:{})};notes=notes.map(row=>row.id===noteId?result:row);if($('#voice-note-save'))$('#voice-note-save').textContent=newer?'Newer edits are being saved…':'Spoken notes saved with this paper in Obsidian.';if(newer){await recoverText(scope,selected);clearTimeout(saveTimer);saveTimer=setTimeout(()=>saveText(scope,selected),200);return false;}else await recovery.remove('text-'+noteId);
    }else await recovery.remove('text-'+noteId);return true;
   }catch(error){await recoverText(scope,{...note,...sent});if(same(scope)){message('Your note edits are kept in this browser. '+error.message,true);if($('#voice-note-save'))$('#voice-note-save').textContent='Not saved to Obsidian yet. Reopen these notes to retry.';}return false;}
  });return saveChain;
 }
 async function choose(note){const scope=view;if(!scope||!note)return;if(!await saveText(scope,selected)||!same(scope))return;selected=note;const pending=await recovery.list(scope.paperId,scope.sectionId);if(!same(scope)||selected?.id!==note.id)return;const saved=pending.find(row=>row.kind==='text'&&row.note_id===note.id);if(saved){const conflict=saved.base_hash!==note.hash&&(saved.corrected_text!==(note.corrected_text||'')||saved.ideas_text!==(note.ideas_text||''));selected={...note,corrected_text:saved.corrected_text,ideas_text:saved.ideas_text,_dirty:true,_conflict:conflict,_vault_text:note.corrected_text,_vault_ideas:note.ideas_text};if(conflict)message('Recovered note edits differ from the saved version. Compare them before saving over changes.',true);}editor();drawHistory();}
 async function refresh(scope){try{const result=await api(path(scope)+'?section_id='+enc(scope.sectionId)+'&include_trashed=true');if(!same(scope))return;notes=result.notes||[];if(selected&&!selected._dirty){const found=notes.find(note=>note.id===selected.id);if(found&&JSON.stringify(found)!==JSON.stringify(selected)){selected=found;editor();}}drawHistory();schedulePoll();}catch(e){if(same(scope))message('Could not refresh saved audio. '+e.message,true);}}
 function schedulePoll(){clearTimeout(pollTimer);if(view&&notes.some(note=>activeStates.has(note.status))){const scope=view;pollTimer=setTimeout(()=>refresh(scope),3000);}}
 async function transcribe(scope,note,language=note.language||'auto'){try{const result=await api(noteURL(scope,note)+'/transcribe',{request_key:uid(),language});updateNote(scope,result);if(same(scope))message('Your audio is saved. Transcription continues if you close this panel or change pages.');}catch(e){if(same(scope))message('Audio is saved. '+e.message,true);}}
 async function savedClip(scope,item,doTranscribe=true){
  if(uploading.has(item.key))return;uploading.add(item.key);
  if(statusInfo?.decoder_ready===false){uploading.delete(item.key);if(same(scope)){message('The local audio decoder needs setup before this recording can be saved to Obsidian. Your audio is in browser recovery; you can download it below.',true);await showRecovery();}return;}
  try{const note=await uploadVoiceClip({api,fetcher,path:path(scope),clip:item});await recovery.remove(item.key);if(clip?.key===item.key)clip=null;if(same(scope)){notes=[note,...notes.filter(n=>n.id!==note.id)];if(await saveText(scope,selected)&&same(scope)){selected=note;editor();message('Audio saved with this paper.');}drawHistory();await showRecovery();}if(doTranscribe&&statusInfo?.ready)await transcribe(scope,note);}
  catch(e){if(same(scope)){message('Your audio is kept for recovery. '+e.message,true);await showRecovery();}else toast('Spoken audio could not be saved. Reopen Speak my idea in its section to recover it.');}
  finally{uploading.delete(item.key);}
 }
 async function showRecovery(){if(!view||!dialog?.open)return;const scope=view,rows=await recovery.list(scope.paperId,scope.sectionId);if(!same(scope))return;const audio=rows.filter(row=>row.kind==='audio'&&row.blob?.size&&(!busy()||row.key!==clip?.key));$('#voice-recovery').innerHTML=audio.length?`<h3>Recover unsaved audio</h3><p>These recordings are kept in this browser and have not yet been confirmed saved to Obsidian.</p>${audio.map(row=>`<div class="voice-recover-row"><span>${esc(row.title||'Spoken idea')} · ${time(row.duration_seconds||0)}</span><button class="btn secondary" data-voice-recover="${esc(row.key)}">Save recovered audio</button><button class="btn quiet" data-voice-download="${esc(row.key)}">Download audio</button></div>`).join('')}`:'';
  $('#voice-recovery').querySelectorAll('[data-voice-recover]').forEach(button=>button.onclick=()=>savedClip(scope,audio.find(row=>row.key===button.dataset.voiceRecover)));
  $('#voice-recovery').querySelectorAll('[data-voice-download]').forEach(button=>button.onclick=()=>{const item=audio.find(row=>row.key===button.dataset.voiceDownload),url=URL.createObjectURL(item.blob),a=document.createElement('a');a.href=url;a.download=item.filename||'spoken-idea.webm';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);});
 }
 function newClip(scope,language){return {key:uid(),kind:'audio',paper_id:scope.paperId,section_id:scope.sectionId,idea_id:scope.ideaId||'',title:('Spoken idea · '+(scope.ideaTitle||scope.sectionTitle||'Section')).slice(0,160),language,created:new Date().toISOString()};}
 async function start(){
  if(busy())return;const scope=view;clip=newClip(scope,$('#voice-language').value);const item=clip;
  capture=new VoiceCapture({onState:state=>{controls();if(state==='stopped'&&capture?.runtimeError)void stopRecording();},onChunk:async(blob,duration)=>{item.blob=blob;item.duration_seconds=duration;item.filename=blob.type.includes('mp4')?'spoken-idea.m4a':blob.type.includes('ogg')?'spoken-idea.ogg':'spoken-idea.webm';const durable=await recovery.put({...item});if(!durable&&same(scope))message('Browser recovery is unavailable. Keep this tab open until your recording is saved, or download it before leaving.',true);if(blob.size>MAX_BYTES)stopRecording().catch(()=>{});}});
  try{const started=await capture.start();if(!started)return;message('Speak in your own words. Your audio stays local; no text is inserted in your draft.');clockTimer=setInterval(()=>{controls();if(capture?.duration()>=MAX_SECONDS-1)stopRecording().catch(()=>{});},300);}
  catch(error){capture=null;controls();message(error.message,true);}
 }
 async function stopRecording(){
  if(!capture)return;const session=capture,item=clip,scope=item?{...view,paperId:item.paper_id,sectionId:item.section_id}:view;clearInterval(clockTimer);
  const blob=await session.stop();if(capture===session)capture=null;controls();
  if(blob?.size&&item){item.blob=blob;item.duration_seconds=session.duration();await recovery.put({...item});if(session.runtimeError&&same(scope))message(session.runtimeError+' The captured audio is kept.',true);void savedClip(scope,item,true);}else if(item){await recovery.remove(item.key);if(clip?.key===item.key)clip=null;}
 }
 async function importAudio(file){if(!file)return;if(file.size>(statusInfo?.max_upload_bytes||MAX_BYTES)){message('Choose audio smaller than 40 MB. Your original file is unchanged.',true);return;}const scope=view,item={...newClip(scope,$('#voice-language').value),blob:file,filename:file.name};await recovery.put(item);void savedClip(scope,item,true);}
 async function open(scope){
  if(dialog?.open)await close();view=scope;returnFocus=document.activeElement;anchor=scope.getAnchor();lastInsertion=null;selected=null;notes=[];showTrashed=false;mergeIds=[];mergeTitle='Merged spoken idea';mergeRequest=null;
  if(!dialog){dialog=document.createElement('dialog');dialog.className='voice-drawer';dialog.setAttribute('aria-labelledby','voice-title');document.body.append(dialog);dialog.addEventListener('cancel',event=>{event.preventDefault();void close();});}
  dialog.innerHTML=`<header class="voice-head"><div><span class="voice-kicker">My own spoken notes</span><h2 id="voice-title">Speak my idea</h2><p>${esc(scope.ideaTitle||scope.sectionTitle||'This section')}</p></div><button class="btn quiet" id="voice-close" aria-label="Close spoken notes">Close</button></header><div class="voice-body"><p>Explain the idea aloud, then use your notes to write. This is your material, separate from the outline, tutor advice and manuscript.</p><div class="voice-record-tools"><label class="field">Spoken language<select id="voice-language"><option value="auto">Auto-detect</option><option value="en">English</option><option value="de">German</option><option value="pl">Polish</option></select></label><button class="btn voice-record-button" id="voice-record">● Record my idea</button><button class="btn secondary" id="voice-pause" hidden>Pause</button><button class="btn secondary" id="voice-stop" hidden>Stop & save audio</button><button class="btn quiet" id="voice-import">Import audio</button><input type="file" id="voice-file" accept="audio/*,.m4a,.mp3,.wav,.webm,.ogg,.mp4" hidden></div><p class="tiny">Up to 10 minutes or 40 MB. Audio is saved first; local transcription follows when available.</p><div id="voice-recording" class="voice-recording" role="status" hidden><span class="voice-recording-dot" aria-hidden="true"></span><strong id="voice-recording-label"></strong><span id="voice-duration" aria-live="off">0:00</span></div><p id="voice-notice" class="voice-notice" role="status"></p><details class="voice-setup"><summary>Local transcription setup</summary><div id="voice-setup-status">Checking setup…</div><button class="btn quiet" id="voice-refresh-setup">Check setup again</button></details><div id="voice-recovery"></div><div id="voice-editor" hidden></div><details class="voice-history" open><summary>Saved spoken notes for this section</summary><label class="voice-trash-filter"><input type="checkbox" id="voice-show-trashed"> Include recordings in trash</label><div id="voice-history"></div></details><details class="voice-manage"><summary>Manage recordings · merge clips</summary><div id="voice-management"></div></details></div>`;
  $('#voice-close').onclick=()=>close();$('#voice-record').onclick=()=>start();$('#voice-pause').onclick=()=>{try{capture?.state==='paused'?capture.resume():capture?.pause();}catch(e){message(e.message,true);}};$('#voice-stop').onclick=()=>stopRecording();$('#voice-import').onclick=()=>$('#voice-file').click();$('#voice-file').onchange=e=>{const file=e.target.files?.[0];e.target.value='';void importAudio(file);};$('#voice-refresh-setup').onclick=()=>loadSetup();$('#voice-show-trashed').onchange=e=>{showTrashed=e.target.checked;drawHistory();};
  dialog.showModal();await Promise.all([loadSetup(),refresh(scope),showRecovery()]);if(same(scope)&&!selected){const first=notes.find(note=>!note.trashed);if(first)await choose(first);}
 }
 async function loadSetup(){try{statusInfo=await api('/voice/status');if(dialog?.open){$('#voice-setup-status').innerHTML=statusMarkup();if(!statusInfo.ready)$('#voice-setup-status').closest('details').open=true;editor();}}catch(e){statusInfo={ready:false,message:e.message};if(dialog?.open){$('#voice-setup-status').innerHTML=statusMarkup();$('#voice-setup-status').closest('details').open=true;}}}
 async function close({requireSaved=false}={}){const scope=view;if(!scope)return true;clearTimeout(saveTimer);return finishVoiceNotes({requireSaved,save:()=>saveText(scope,selected),close:async()=>{await stopRecording();clearTimeout(pollTimer);dialog?.close();view=null;selected=null;returnFocus?.isConnected&&returnFocus.focus();}});}
 if(typeof window!=='undefined')window.addEventListener('beforeunload',event=>{if(busy()||uploading.size||selected?._dirty){event.preventDefault();event.returnValue='';}});
 if(typeof window!=='undefined')window.addEventListener('pagehide',()=>{capture?.stop().catch(()=>{});});
 return {open,leave:close,close,hasRecording:busy};
}
