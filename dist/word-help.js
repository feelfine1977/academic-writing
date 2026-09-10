import {selectedPhrase,canApplyWord} from './word-selection.js';
export function mountWordHelp({api,esc,node,editors,current}){
 const key='awl-word-help-'+node.id;
 let target=null,snapshot=null,panel,poll,serial=0,undo=null;
 const readKey=()=>{try{return localStorage.getItem(key)}catch{return null}};
 const keepKey=id=>{try{localStorage.setItem(key,id)}catch{}};
 function ensurePanel(editor){
  if(!panel){panel=document.createElement('section');panel.className='word-help-panel';panel.setAttribute('aria-label','Local word help');}
  editor.closest('label').after(panel);panel.hidden=false;
 }
 function capture(editor){target=editor;snapshot=selectedPhrase(editor.value,editor.selectionStart,editor.selectionEnd);return snapshot;}
 function open(editor){
  clearTimeout(poll);serial++;capture(editor);ensurePanel(editor);
  panel.innerHTML=`<div class="section-row"><h3>Word help in this sentence</h3><button class="btn quiet" data-close>Close</button></div><p class="tiny">Select a word or short phrase, then ask the local tutor. Your text changes only if you choose a replacement.</p><p data-selection></p><button class="btn secondary" data-ask>Ask for word choices</button><div data-word-result role="status"></div>`;
  panel.querySelector('[data-selection]').textContent=snapshot?'Selected: “'+snapshot.selected+'”':'No word selected. Select a word in your text and press Word help again.';
  panel.querySelector('[data-close]').onclick=()=>{panel.hidden=true;editor.focus({preventScroll:true})};
  const ask=panel.querySelector('[data-ask]');ask.disabled=!snapshot;
  panel.scrollIntoView({block:'nearest',behavior:'smooth'});
  ask.onclick=async()=>{
   const own=++serial;ask.disabled=true;
   panel.querySelector('[data-word-result]').textContent='Requesting local word help… You can keep writing.';
   try{const job=await api('/paper/word-help',{node_id:node.id,selected:snapshot.selected,before:snapshot.before,after:snapshot.after});keepKey(job.id);if(current()&&own===serial)show(job,own)}
   catch(e){if(current()&&own===serial){panel.querySelector('[data-word-result]').textContent=e.message;ask.disabled=false}}
  };
 }
 function show(job,own){
  if(!current()||own!==serial)return;
  const result=panel.querySelector('[data-word-result]');
  if(['queued','running'].includes(job.status)){
   result.textContent=job.status==='queued'?'Waiting for the local tutor. You can keep writing; word help will appear here.':'Reading your selected phrase in context… You can keep writing.';
   poll=setTimeout(async()=>{try{show(await api('/paper/word-help/'+job.id),own)}catch(e){if(current()&&own===serial){result.textContent=e.message;panel.querySelector('[data-ask]').disabled=!snapshot}}},1500);return;
  }
  panel.querySelector('[data-ask]').disabled=!snapshot;
  if(job.status!=='complete'){result.textContent=job.error||'Word help did not complete.';return}
  const r=job.result;
  result.innerHTML=`<p>${esc(r.original_assessment)}</p>${r.meaning_question?`<p><strong>Meaning to check:</strong> ${esc(r.meaning_question)}</p>`:''}<div class="word-alternatives">${r.alternatives.map((a,i)=>`<article><strong>${esc(a.replacement)}</strong><p>${esc(a.explanation)}</p><button class="btn secondary" data-apply="${i}">Use “${esc(a.replacement)}”</button></article>`).join('')}</div><p class="tiny" data-stale></p><button class="btn quiet" data-undo hidden>Undo replacement</button><p class="tiny">Local tutor suggestion · choose the wording that preserves your meaning. Save your paragraph or notes when ready.</p>`;
  const freshness=()=>{
   const valid=canApplyWord(snapshot,target?.value);
   result.querySelectorAll('[data-apply]').forEach(b=>b.disabled=!valid);
   result.querySelector('[data-stale]').textContent=valid?'Applies only to the selected word or phrase.':'Your text has changed or this is an earlier request. Select the word again for a fresh suggestion; these suggestions remain available to read.';
  };
  freshness();
  result.querySelectorAll('[data-apply]').forEach(b=>b.onclick=()=>{
   if(!canApplyWord(snapshot,target.value)){freshness();return}
   const replacement=r.alternatives[Number(b.dataset.apply)].replacement;
   if(target.value.length-snapshot.selected.length+replacement.length>target.maxLength){result.querySelector('[data-stale]').textContent='This replacement would exceed the editor’s length limit.';return}
   undo={before:target.value,after:null,start:snapshot.start,end:snapshot.end};
   target.setRangeText(replacement,snapshot.start,snapshot.end,'select');undo.after=target.value;
   target.dispatchEvent(new Event('input',{bubbles:true}));target.focus({preventScroll:true});freshness();result.querySelector('[data-undo]').hidden=false;
  });
  result.querySelector('[data-undo]').onclick=()=>{
   if(!undo||target.value!==undo.after){result.querySelector('[data-stale]').textContent='You have made further edits. Use the editor’s Undo command or restore the word manually.';return}
   target.value=undo.before;target.setSelectionRange(undo.start,undo.end);target.dispatchEvent(new Event('input',{bubbles:true}));target.focus({preventScroll:true});undo=null;result.querySelector('[data-undo]').hidden=true;freshness();
  };
  // Only update disabled states; never re-render the editor or move focus on arrival.
  target?.addEventListener('input',freshness,{signal:controller.signal});
 }
 const controller=new AbortController();
 for(const editor of editors.filter(Boolean)){
  const bar=document.createElement('div');bar.className='word-help-tools';
  bar.innerHTML='<button type="button" class="btn quiet">Word help for selection</button><span class="tiny">Select a word · right-click or use this button</span>';
  editor.closest('label').before(bar);bar.querySelector('button').onclick=()=>open(editor);
  editor.addEventListener('contextmenu',event=>{if(event.shiftKey||editor.selectionStart===editor.selectionEnd)return;event.preventDefault();open(editor)},{signal:controller.signal});
 }
 // Recover advice after leaving the desk, without assuming its saved offsets still match.
 const previous=readKey();
 if(previous&&editors[0]){
  const button=document.createElement('button');button.className='btn quiet';button.textContent='Previous word help';editors[0].closest('label').after(button);
  button.onclick=async()=>{open(editors[0]);snapshot=null;panel.querySelector('[data-ask]').disabled=true;const own=serial;try{const job=await api('/paper/word-help/'+previous);if(current()&&own===serial){panel.querySelector('[data-selection]').textContent='Earlier selection: “'+job.selected+'”';show(job,own)}}catch(e){if(current())panel.querySelector('[data-word-result]').textContent=e.message}};
 }
 window.addEventListener('hashchange',()=>{clearTimeout(poll);controller.abort()},{once:true});
}
