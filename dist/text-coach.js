import {discussionScope,proposedText,proposalState,recoverDiscussion} from './text-coach-state.js';
function checkHTML(check,esc){
 const titles={checked:'Separate edit check: no regression identified',needs_attention:'The suggested edit needs attention',unavailable:'The edit check did not finish',checking:'Checking the suggested edit'};
 if(!check)return '<p class="alert">Earlier suggestion: meaning preservation was not checked. Read the comparison before using the wording.</p>';
 const reason=check.status==='unavailable'?'The optional comparison did not finish or could not be validated. It has no verdict on this wording.':check.reason||'';
 return `<div class="edit-check ${check.apply_allowed?'checked':'needs-attention'}"><strong>${titles[check.status]||'Review this edit'}</strong><p>${esc(reason)}</p>${check.unresolved_task_criteria?.length?'<p class="tiny">Some task judgements remain unresolved in both versions. This check concerns the edit; it does not settle those questions.</p>':''}${(check.meaning_changes||[]).length?`<details><summary>What changed in meaning?</summary>${check.meaning_changes.map(c=>`<p><strong>${esc(c.effect)}:</strong> ${esc(c.explanation)}</p>${c.original_quote?`<small>Original</small><blockquote>${esc(c.original_quote)}</blockquote>`:''}${c.revised_quote?`<small>Proposed</small><blockquote>${esc(c.revised_quote)}</blockquote>`:''}`).join('')}</details>`:''}<p class="tiny">A separate local-model comparison under the task criteria. It does not award completion or guarantee a future review.</p></div>`;
}
export function mountTextCoach({api,esc,editor,exerciseKey,nodeId=null,current}){
 if(!editor)return;
 const key='awl-writing-question-'+exerciseKey,controller=new AbortController();
 let panel=null,snapshot=null,poll=null,serial=0,undo=null,renderedJob='',refreshProposalState=null;
 const get=suffix=>{try{return localStorage.getItem(key+suffix)||''}catch{return ''}};
 const put=(suffix,value)=>{try{localStorage.setItem(key+suffix,value)}catch{}};
 const controls=document.createElement('div');controls.className='text-coach-tools';
 const button=document.createElement('button');button.type='button';button.className='btn secondary';button.textContent='Ask about my text';
 const previous=document.createElement('button');previous.type='button';previous.className='btn quiet';previous.textContent='Previous writing question';previous.hidden=!get('-job');controls.append(button,previous);
 const anchor=editor.closest('label')||editor;anchor.before(controls);
 const presetQuestions=[['Shorten','How could I make this shorter without losing the meaning or making the writing less natural? Consider splitting long sentences.'],['Improve flow','How could I make the connections between these sentences clearer while preserving my argument?'],['Check wording','Which words or phrases could be more natural and precise? Keep wording that already works.']];
 function createPanel(){
  if(panel?.isConnected)return;
  panel=document.createElement('section');panel.className='text-coach-panel';panel.setAttribute('aria-label','Ask about my text');anchor.after(panel);
 }
 function open(whole=false){
  clearTimeout(poll);serial++;renderedJob='';createPanel();panel.hidden=false;
  snapshot=discussionScope(editor.value,editor.selectionStart,editor.selectionEnd,whole);undo=null;
  panel.innerHTML=`<div class="section-row"><h3>Ask about my text</h3><button class="btn quiet" data-close>Close</button></div><p class="tiny">Ask for suggestions at any stage, including after completing an activity. This coaching does not grade or replace your saved answer.</p><div class="actions"><button class="btn quiet" data-selected>Use selected text</button><button class="btn quiet" data-whole>Use whole paragraph</button></div><details class="question-source"><summary data-scope></summary><p class="prose" data-source></p></details><label class="field">Your question<textarea data-question rows="3" maxlength="1500" placeholder="For example: Can I split this sentence without losing the connection between the ideas?"></textarea></label><div class="actions">${presetQuestions.map(([label],i)=>`<button class="btn quiet" data-preset="${i}">${label}</button>`).join('')}</div><button class="btn" data-ask>Ask the local tutor</button><p class="tiny" data-question-status role="status"></p><div data-coach-result></div>`;
  panel.querySelector('[data-source]').textContent=snapshot.selected||'There is no text yet.';
  panel.querySelector('[data-scope]').textContent=snapshot.scope+' · '+snapshot.selected.trim().split(/\s+/).filter(Boolean).length+' words · text sent with your question';
  const question=panel.querySelector('[data-question]');question.value=get('-prompt');question.oninput=()=>put('-prompt',question.value);
  panel.querySelector('[data-close]').onclick=()=>{panel.hidden=true;editor.focus({preventScroll:true})};
  panel.querySelector('[data-whole]').onclick=()=>open(true);
  panel.querySelector('[data-selected]').onclick=()=>{
   if(editor.selectionStart===editor.selectionEnd){panel.querySelector('[data-question-status]').textContent='Select a sentence in your editor, then click Use selected text.';return}open(false);
  };
  for(const b of panel.querySelectorAll('[data-preset]'))b.onclick=()=>{question.value=presetQuestions[Number(b.dataset.preset)][1];question.dispatchEvent(new Event('input'));question.focus()};
  panel.querySelector('[data-ask]').onclick=async()=>{
   if(!question.value.trim()||!snapshot.selected.trim()){panel.querySelector('[data-question-status]').textContent='Add your text and a question first.';return}
   const own=++serial,submitted=snapshot;panel.querySelector('[data-ask]').disabled=true;
   panel.querySelector('[data-question-status]').textContent='Saving your question… You can keep writing.';panel.querySelector('[data-coach-result]').replaceChildren();
   try{const job=await api('/writing-questions',{exercise_key:exerciseKey,node_id:nodeId,text:submitted.selected,question:question.value,full_text:submitted.text,selection_start:submitted.start,outline:document.querySelector('#outline')?.value,before:submitted.text.slice(Math.max(0,submitted.start-700),submitted.start),after:submitted.text.slice(submitted.end,submitted.end+700)});
    put('-job',job.id);previous.hidden=false;if(current()&&serial===own)show(job,submitted,own);
   }catch(e){if(current()&&serial===own){panel.querySelector('[data-question-status]').textContent=e.message;panel.querySelector('[data-ask]').disabled=false}}
  };
  panel.scrollIntoView({block:'nearest',behavior:'smooth'});question.focus({preventScroll:true});
 }
 function show(job,submitted,own){
  if(!current()||own!==serial||!panel?.isConnected)return;
  const status=panel.querySelector('[data-question-status]'),result=panel.querySelector('[data-coach-result]');
  const pending=['queued','running'].includes(job.status);
  if(pending){
   status.textContent=(job.status==='queued'?'Waiting for the local tutor.':job.stage==='checking_suggestions'?'Draft suggestions are ready. A separate reading is checking meaning and the same task criteria…':'Considering your question…')+' Your text stays editable. You can find this again under Previous writing question.';
   poll=setTimeout(async()=>{try{show(await api('/writing-questions/'+job.id),submitted,own)}catch(e){if(current()&&own===serial){status.textContent=e.message;panel.querySelector('[data-ask]').disabled=false}}},1600);
   if(!job.result)return;
  }
  panel.querySelector('[data-ask]').disabled=pending;
  if(!pending&&job.status!=='complete'&&!job.result){status.textContent=job.error||'The question did not finish.';return}
  if(!pending)status.textContent=undo?'Suggestion applied to your draft. The optional check has finished; Undo is still available.':'Suggestions ready. Choose wording below to use in your editable draft. Saved versions stay unchanged.';
  const renderKey=job.id+':'+job.status+':'+job.stage;
  if(renderedJob===renderKey)return;
  renderedJob=renderKey;
  const r={...job.result,suggestions:job.result.suggestions.map(s=>!pending&&s.check?.status==='checking'?{...s,check:{status:'unavailable',apply_allowed:false}}:s)};
  result.innerHTML=`<h4>Your question</h4><p>${esc(job.question)}</p><p class="question-answer">${esc(r.answer)}</p>${r.strengths.length?'<h4>Keep what works</h4>':''}${r.strengths.map(s=>`<div class="strength"><blockquote>${esc(s.quote)}</blockquote><p>${esc(s.explanation)}</p></div>`).join('')}${r.meaning_questions.length?`<h4>Meaning to check before editing</h4><ul>${r.meaning_questions.map(q=>`<li>${esc(q)}</li>`).join('')}</ul>`:''}${r.suggestions.length?'<h4>Optional revisions</h4>':''}${r.suggestions.map((s,i)=>`<article class="coach-proposal">${checkHTML(s.check,esc)}<div class="coach-comparison"><div><small>Current wording</small><p class="prose">${esc(s.quote)}</p></div><div><small>Proposed wording</small><p class="prose">${esc(s.replacement)}</p></div></div><p>${esc(s.explanation)}</p><p class="tiny"><strong>Meaning:</strong> ${esc(s.meaning_note)}</p><button class="btn secondary" data-use="${i}" aria-describedby="coach-use-${own}-${i}">Use this suggestion</button><p class="tiny" id="coach-use-${own}-${i}" data-use-reason="${i}" role="status"></p></article>`).join('')}<p class="tiny" data-freshness></p><button class="btn quiet" data-undo ${undo?'':'hidden'}>Undo suggested edit</button><p class="tiny">Local AI coaching · suggestions are not verified research claims or an exercise score. Save your edited text when ready.</p>`;
  const freshness=()=>{
   if(!result.isConnected||own!==serial)return;
   for(const b of result.querySelectorAll('[data-use]')){
    const i=Number(b.dataset.use),state=proposalState(submitted,r.suggestions[i],editor.value),applied=undo?.index===i&&editor.value===undo.after;
    b.disabled=!state.next;b.textContent=applied?'Applied to draft':'Use this suggestion';
    result.querySelector(`[data-use-reason="${i}"]`).textContent=applied?'This wording is in your editor. Undo restores the previous text; save when ready.':state.notice;
   }
   result.querySelector('[data-freshness]').textContent='Meaning checks are advice. Applying a suggestion never saves or submits an answer automatically.';
  };if(refreshProposalState)editor.removeEventListener('input',refreshProposalState);refreshProposalState=freshness;freshness();editor.addEventListener('input',freshness,{signal:controller.signal});
  for(const b of result.querySelectorAll('[data-use]'))b.onclick=()=>{
   const next=proposedText(submitted,r.suggestions[Number(b.dataset.use)],editor.value);if(!next){freshness();return}
   if(editor.maxLength>=0&&next.text.length>editor.maxLength){status.textContent='This change would exceed the editor’s length limit.';return}
   undo={before:editor.value,after:next.text,index:Number(b.dataset.use)};editor.value=next.text;editor.setSelectionRange(next.start,next.end);editor.dispatchEvent(new Event('input',{bubbles:true}));editor.focus({preventScroll:true});
   result.querySelector('[data-undo]').hidden=false;status.textContent='Suggestion applied to your editor only. Save it when ready.';freshness();
  };
  result.querySelector('[data-undo]').onclick=()=>{
   if(!undo||editor.value!==undo.after){status.textContent='Further edits are present. Restore the wording manually so those edits are preserved.';return}
   editor.value=undo.before;undo=null;editor.dispatchEvent(new Event('input',{bubbles:true}));editor.focus({preventScroll:true});result.querySelector('[data-undo]').hidden=true;status.textContent='Suggested edit undone.';freshness();
  };
 }
 button.onclick=()=>open();
 previous.onclick=async()=>{
  open(true);const own=serial;
  try{const job=await api('/writing-questions/'+get('-job'));if(!current()||serial!==own)return;
   panel.querySelector('[data-question]').value=job.question;panel.querySelector('[data-source]').textContent=job.text;panel.querySelector('[data-scope]').textContent='Previously submitted text';
   // Reuse only an exact saved context, including its original selection offsets.
   const recovered=recoverDiscussion(job,editor.value);snapshot=recovered||discussionScope(editor.value);show(job,recovered,own);
  }catch(e){if(current()&&own===serial)panel.querySelector('[data-question-status]').textContent=e.message}
 };
 window.addEventListener('hashchange',()=>{clearTimeout(poll);controller.abort()},{once:true});
}
