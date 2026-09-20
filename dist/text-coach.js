import {discussionScope,proposedText,proposalState,recoverDiscussion} from './text-coach-state.js';
function checkHTML(check,esc){
 const titles={checked:'Separate edit check: no regression identified',needs_attention:'The suggested edit needs attention',unavailable:'The edit check did not finish',checking:'Checking the suggested edit'};
 if(!check)return '<p class="alert">Earlier suggestion: meaning preservation was not checked. Read the comparison before using the wording.</p>';
 const reason=check.status==='unavailable'?'The optional comparison did not finish or could not be validated. It has no verdict on this wording.':check.reason||'';
 return `<div class="edit-check ${check.apply_allowed?'checked':'needs-attention'}"><strong>${titles[check.status]||'Review this edit'}</strong><p>${esc(reason)}</p>${check.unresolved_task_criteria?.length?'<p class="tiny">Some task judgements remain unresolved in both versions. This check concerns the edit; it does not settle those questions.</p>':''}${(check.meaning_changes||[]).length?`<details><summary>What changed in meaning?</summary>${check.meaning_changes.map(c=>`<p><strong>${esc(c.effect)}:</strong> ${esc(c.explanation)}</p>${c.original_quote?`<small>Original</small><blockquote>${esc(c.original_quote)}</blockquote>`:''}${c.revised_quote?`<small>Proposed</small><blockquote>${esc(c.revised_quote)}</blockquote>`:''}`).join('')}</details>`:''}<p class="tiny">A separate local-model comparison under the task criteria. It does not award completion or guarantee a future review.</p></div>`;
}
const defaultQuestions=[['Shorten','How could I make this shorter without losing the meaning or making the writing less natural? Consider splitting long sentences.'],['Improve flow','How could I make the connections between these sentences clearer while preserving my argument?'],['Check wording','Which words or phrases could be more natural and precise? Keep wording that already works.']];
export function coachSnapshotNote(submitted,text){
 if(!submitted)return '';
 return submitted.text===text?'Your editor matches the text submitted for this feedback.':'Your text has changed since this question. This feedback refers to the earlier text; ask again to review your current draft.';
}
export function tutorCoverageNote(job){
 const text=String(job.text||''),count=text.trim().split(/\s+/).filter(Boolean).length;
 const scope=text===job.original_text?'Whole paragraph':'Selected passage';
 const fields=job.result?.context_limits?.shortened_fields||[];
 const labels={argument_notes:'argument notes',plan_questions:'planning questions',supervisor_comments:'meeting guidance',reviewer_guidance:'reviewer notes',neighbouring_drafts:'neighbouring drafts'};
 return `${scope}: ${count} words submitted intact. Feedback highlights selected points.`+(fields.length?' Background shortened: '+fields.map(x=>labels[x]||x.replaceAll('_',' ')).join(', ')+'.':'');
}
export function reviewFocusForPreset(preset){return ['evidence','structure'].includes(preset?.[2])?preset[2]:'general';}
export function structureFeedbackHTML(result,esc){
 const labels={draft:'Your draft',current_brief:'Current writing brief',meeting_guidance:'Meeting guidance',reviewer_guidance:'AI reviewer suggestion',neighbouring_draft:'Neighbouring draft'};
 return `<p>${esc(result.answer)}</p>${(result.structure_observations||[]).map(o=>`<article class="coach-evidence-check"><p class="tiny">Based on: ${esc(labels[o.basis]||o.basis)}</p>${o.quote?`<blockquote>${esc(o.quote)}</blockquote>`:''}<p>${esc(o.explanation)}</p><p><strong>Writing action:</strong> ${esc(o.writing_action)}</p></article>`).join('')}<p><strong>One next step:</strong> ${esc(result.next_step)}</p>`;
}
export function evidenceFeedbackHTML(checks,esc){
 const labels={supported:'Supported by this passage',partly_supported:'Only partly supported',not_established:'Not established by the attached passages'};
 return checks.map(check=>`<article class="coach-evidence-check"><h4>Claim in your text</h4><blockquote>${esc(check.claim)}</blockquote><p><strong>Tutor assessment: ${esc(labels[check.support]||check.support)}</strong></p>${check.source_quote?`<details open><summary>Compare with the source passage</summary><blockquote class="coach-evidence-quote">${esc(check.source_quote)}</blockquote><p class="tiny">${esc(check.source_title)}${check.source_location?' · '+esc(check.source_location.replace(/\*\*/g,'')):''}</p></details>`:''}<p>${esc(check.explanation)}</p><p><strong>Your next step:</strong> ${esc(check.next_step)}</p></article>`).join('');
}
export function mountTextCoach({api,esc,editor,exerciseKey,nodeId=null,current=()=>true,host=null,storageKey=null,historyContext=null,prepareRequest=null,presetQuestions=defaultQuestions,contextNote='',introNote='Ask for suggestions at any stage, including after completing an activity. This coaching does not grade or replace your saved answer.'}){
 if(!editor)return {open(){},dispose(){}};
 const key=storageKey||'awl-writing-question-'+exerciseKey,controller=new AbortController();
 let panel=null,snapshot=null,reviewSnapshot=null,poll=null,serial=0,undo=[],renderedJob='',refreshProposalState=null,disposed=false;
 const alive=()=>!disposed&&current();
 const get=suffix=>{try{return localStorage.getItem(key+suffix)||''}catch{return ''}};
 const put=(suffix,value)=>{try{localStorage.setItem(key+suffix,value)}catch{}};
 let reviewFocus=['evidence','structure'].includes(get('-focus'))?get('-focus'):'general';
 function drawReviewFocus(){
  const note=panel?.querySelector('[data-review-focus]');if(!note)return;
  note.hidden=reviewFocus==='general';note.textContent=reviewFocus==='structure'?'Structure tutor: the purpose, guidance and adjacent drafts; writing actions, no rewrites.':'Evidence tutor: compare claims and passages; no manuscript rewrites.';
  panel.querySelectorAll('[data-preset]').forEach(b=>b.setAttribute('aria-pressed',String(reviewFocusForPreset(presetQuestions[Number(b.dataset.preset)])===reviewFocus)));
 }
 const controls=document.createElement('div');controls.className='text-coach-tools';
 const button=document.createElement('button');button.type='button';button.className='btn secondary';button.textContent='Ask about my text';
 const previous=document.createElement('button');previous.type='button';previous.className='btn quiet';previous.textContent='Previous writing question';previous.hidden=!get('-job');controls.append(button,previous);
 const history=document.createElement('select');history.hidden=true;history.setAttribute('aria-label','Saved writing questions from this writing task');controls.append(history);
 const anchor=editor.closest('label')||editor;if(host)host.append(controls);else anchor.before(controls);
 function createPanel(){
  if(panel?.isConnected)return;
  panel=document.createElement('section');panel.className='text-coach-panel';panel.setAttribute('aria-label','Ask about my text');if(host)host.append(panel);else anchor.after(panel);
 }
 function refreshSnapshot(){
  const label=panel?.querySelector('[data-snapshot-status]');if(label)label.textContent=coachSnapshotNote(reviewSnapshot,editor.value);
 }
 editor.addEventListener('input',refreshSnapshot,{signal:controller.signal});
 function open(whole=false){
  if(!alive())return;
  clearTimeout(poll);serial++;renderedJob='';reviewSnapshot=null;
  if(refreshProposalState){editor.removeEventListener('input',refreshProposalState);refreshProposalState=null}
  createPanel();panel.hidden=false;
  snapshot=discussionScope(editor.value,editor.selectionStart,editor.selectionEnd,whole);undo=[];
  panel.innerHTML=`<div class="section-row"><h3>Ask about my text</h3><button class="btn quiet" data-close>Close</button></div>${introNote?`<p class="tiny">${esc(introNote)}</p>`:''}${contextNote?`<p class="tiny text-coach-context">${esc(contextNote)}</p>`:''}<div class="actions"><button class="btn quiet" data-selected>Use selected text</button><button class="btn quiet" data-whole>Use whole paragraph</button></div><details class="question-source"><summary data-scope></summary><p class="prose" data-source></p></details><label class="field">Your question<textarea data-question rows="3" maxlength="1500" placeholder="For example: Can I split this sentence without losing the connection between the ideas?"></textarea></label><div class="actions">${presetQuestions.map(([label],i)=>`<button class="btn quiet" data-preset="${i}">${label}</button>`).join('')}</div><button class="btn" data-ask>Ask the local tutor</button><p class="tiny" data-question-status role="status"></p><p class="tiny" data-snapshot-status role="status"></p><div data-coach-result></div>`;
  panel.querySelector('[data-source]').textContent=snapshot.selected||'There is no text yet.';
  panel.querySelector('[data-scope]').textContent=snapshot.scope+' · '+snapshot.selected.trim().split(/\s+/).filter(Boolean).length+' words · text sent with your question';
  const question=panel.querySelector('[data-question]');question.value=get('-prompt');question.oninput=()=>put('-prompt',question.value);
  panel.querySelector('[data-ask]').insertAdjacentHTML('beforebegin','<p class="tiny" data-review-focus hidden></p>');drawReviewFocus();
  panel.querySelector('[data-close]').onclick=()=>{panel.hidden=true;editor.focus({preventScroll:true})};
  panel.querySelector('[data-whole]').onclick=()=>open(true);
  panel.querySelector('[data-selected]').onclick=()=>{
   if(editor.selectionStart===editor.selectionEnd){panel.querySelector('[data-question-status]').textContent='Select a sentence in your editor, then click Use selected text.';return}open(false);
  };
  for(const b of panel.querySelectorAll('[data-preset]'))b.onclick=()=>{const preset=presetQuestions[Number(b.dataset.preset)];reviewFocus=reviewFocusForPreset(preset);put('-focus',reviewFocus);drawReviewFocus();question.value=preset[1];question.dispatchEvent(new Event('input'));question.focus()};
  panel.querySelector('[data-ask]').onclick=async()=>{
   if(!alive())return;
   if(snapshot.scope==='Whole paragraph')snapshot=discussionScope(editor.value,0,0,true);
   else if(snapshot.text!==editor.value){panel.querySelector('[data-question-status]').textContent='Your selected text has changed. Select it again and choose Use selected text, or use the whole paragraph.';return}
   if(!question.value.trim()||!snapshot.selected.trim()){panel.querySelector('[data-question-status]').textContent='Add your text and a question first.';return}
   const own=++serial,submitted=snapshot,writerQuestion=question.value,writerFocus=reviewFocus;reviewSnapshot=submitted;refreshSnapshot();panel.querySelector('[data-ask]').disabled=true;
   panel.querySelector('[data-source]').textContent=submitted.selected;
   panel.querySelector('[data-scope]').textContent=submitted.scope+' · '+submitted.selected.trim().split(/\s+/).length+' words · text sent with your question';
   panel.querySelector('[data-question-status]').textContent='Saving your question… You can keep writing.';panel.querySelector('[data-coach-result]').replaceChildren();
   try{
    const prepared=prepareRequest?await prepareRequest({snapshot:submitted,question:writerQuestion}):{};
    if(!alive()||serial!==own)return;
    const requestKey=prepared?.exerciseKey||exerciseKey;if(!requestKey)throw new Error('This writing task could not be prepared. Your text stays in the editor.');
    const job=await api('/writing-questions',{exercise_key:requestKey,node_id:prepared?.nodeId??nodeId,text:submitted.selected,question:writerQuestion,review_focus:writerFocus,full_text:submitted.text,selection_start:submitted.start,outline:prepared?.outline??document.querySelector('#outline')?.value,before:submitted.text.slice(Math.max(0,submitted.start-700),submitted.start),after:submitted.text.slice(submitted.end,submitted.end+700)});
    put('-job',job.id);previous.hidden=false;if(alive()&&serial===own)show(job,submitted,own);
   }catch(e){if(alive()&&serial===own){panel.querySelector('[data-question-status]').textContent=e.message;panel.querySelector('[data-ask]').disabled=false}}
  };
  if(!host)panel.scrollIntoView({block:'nearest',behavior:'smooth'});question.focus({preventScroll:true});
 }
 function show(job,submitted,own){
  if(!alive()||own!==serial||!panel?.isConnected)return;
  const status=panel.querySelector('[data-question-status]'),result=panel.querySelector('[data-coach-result]');
  const pending=['queued','running'].includes(job.status);
  if(pending){
   status.textContent=(job.status==='queued'?'Waiting for the local tutor.':job.stage==='checking_suggestions'?'Draft suggestions are ready. A separate reading is checking meaning and the same task criteria…':'Considering your question…')+' Your text stays editable. You can find this again under Previous writing question.';
   poll=setTimeout(async()=>{try{show(await api('/writing-questions/'+job.id),submitted,own)}catch(e){if(alive()&&own===serial){status.textContent=e.message;panel.querySelector('[data-ask]').disabled=false}}},1600);
   if(!job.result)return;
  }
  panel.querySelector('[data-ask]').disabled=pending;
  if(!pending&&job.status!=='complete'&&!job.result){status.textContent=job.error||'The question did not finish.';return}
  if(!pending)status.textContent=undo.length?'Suggested edits are in your draft. The optional check has finished; Undo is still available.':'Suggestions ready. Choose wording below to use in your editable draft. Saved versions stay unchanged.';
  const renderKey=job.id+':'+job.status+':'+job.stage;
  if(renderedJob===renderKey)return;
  renderedJob=renderKey;
  const coverage=`<p class="tiny">${esc(tutorCoverageNote(job))}</p>`;
  const r={...job.result,suggestions:job.result.suggestions.map(s=>!pending&&s.check?.status==='checking'?{...s,check:{status:'unavailable',apply_allowed:false}}:s)};
  if(job.review_focus==='structure'&&Array.isArray(r.structure_observations)){
   status.textContent='Structure reading finished. Your wording is unchanged.';
   result.innerHTML=coverage+structureFeedbackHTML(r,esc)+`<p class="tiny">A focused AI reading, not supervisor approval or verification of the literature.${job.provenance?.model?' Model: '+esc(job.provenance.model)+'.':''}</p>`;
   return;
  }
  if(job.review_focus==='evidence'&&Array.isArray(r.evidence_checks)){
   status.textContent='Evidence check finished. Review the claims and passages below.';
   result.innerHTML=coverage+`<p class="question-answer">${esc(r.answer)}</p>${evidenceFeedbackHTML(r.evidence_checks,esc)}${r.source_coverage?.omitted?`<p class="tiny">This reading received ${esc(r.source_coverage.included)} of ${esc(r.source_coverage.available)} attached passages. The other passages were not assessed.</p>`:''}<p class="tiny">The quoted words were matched to your saved text and source passages. The support assessments are the tutor's interpretation; review them before revising or citing.</p>`;
   return;
  }
  result.innerHTML=coverage+`<h4>Your question</h4><p>${esc(job.question)}</p><p class="question-answer">${esc(r.answer)}</p>${r.strengths.length?'<h4>Keep what works</h4>':''}${r.strengths.map(s=>`<div class="strength"><blockquote>${esc(s.quote)}</blockquote><p>${esc(s.explanation)}</p></div>`).join('')}${r.meaning_questions.length?`<h4>Meaning to check before editing</h4><ul>${r.meaning_questions.map(q=>`<li>${esc(q)}</li>`).join('')}</ul>`:''}${r.suggestions.length?'<h4>Optional revisions</h4>':''}${r.suggestions.map((s,i)=>`<article class="coach-proposal">${checkHTML(s.check,esc)}<div class="coach-comparison"><div><small>Current wording</small><p class="prose">${esc(s.quote)}</p></div><div><small>Proposed wording</small><p class="prose">${esc(s.replacement)}</p></div></div><p>${esc(s.explanation)}</p><p class="tiny"><strong>Meaning:</strong> ${esc(s.meaning_note)}</p><button class="btn secondary" data-use="${i}" aria-describedby="coach-use-${own}-${i}">Use this suggestion</button><p class="tiny" id="coach-use-${own}-${i}" data-use-reason="${i}" role="status"></p></article>`).join('')}<p class="tiny" data-freshness></p><button class="btn quiet" data-undo ${undo.length?'':'hidden'}>Undo suggested edit</button><p class="tiny">Local AI coaching · suggestions are not verified research claims or an exercise score. Save your edited text when ready.</p>`;
  const freshness=()=>{
   if(!result.isConnected||own!==serial)return;
   for(const b of result.querySelectorAll('[data-use]')){
    const i=Number(b.dataset.use),state=proposalState(submitted,r.suggestions[i],editor.value,r.suggestions),applied=state.applied;
    b.disabled=!state.next;b.textContent=applied?'Applied to draft':'Use this suggestion';
    result.querySelector(`[data-use-reason="${i}"]`).textContent=applied?'This wording is in your editor. You can continue with suggestions for other passages.':state.notice;
   }
   result.querySelector('[data-freshness]').textContent='You can use suggestions for separate passages one after another. Each meaning check refers to the original draft; it has not checked the combined edits.';
  };if(refreshProposalState)editor.removeEventListener('input',refreshProposalState);refreshProposalState=freshness;freshness();editor.addEventListener('input',freshness,{signal:controller.signal});
  for(const b of result.querySelectorAll('[data-use]'))b.onclick=()=>{
   const next=proposedText(submitted,r.suggestions[Number(b.dataset.use)],editor.value,r.suggestions);if(!next){freshness();return}
   if(editor.maxLength>=0&&next.text.length>editor.maxLength){status.textContent='This change would exceed the editor’s length limit.';return}
   undo.push({before:editor.value,after:next.text});editor.value=next.text;editor.setSelectionRange(next.start,next.end);editor.dispatchEvent(new Event('input',{bubbles:true}));editor.focus({preventScroll:true});
   result.querySelector('[data-undo]').hidden=false;status.textContent='Suggestion applied to your editor only. Save it when ready.';freshness();
  };
  result.querySelector('[data-undo]').onclick=()=>{
   const latest=undo.at(-1);if(!latest||editor.value!==latest.after){status.textContent='Further edits are present. Restore the wording manually so those edits are preserved.';return}
   editor.value=latest.before;undo.pop();editor.dispatchEvent(new Event('input',{bubbles:true}));editor.focus({preventScroll:true});result.querySelector('[data-undo]').hidden=!undo.length;status.textContent='Last suggested edit undone.';freshness();
  };
 }
 button.onclick=()=>open();
 previous.onclick=async()=>{
  open(true);const own=serial;
  try{const job=await api('/writing-questions/'+get('-job'));if(!alive()||serial!==own)return;
   panel.querySelector('[data-question]').value=job.question;panel.querySelector('[data-source]').textContent=job.text;panel.querySelector('[data-scope]').textContent='Previously submitted text';
   reviewFocus=job.review_focus||'general';put('-focus',reviewFocus);drawReviewFocus();
   // Recover the original scope, including recognised edits from this question.
   const recovered=recoverDiscussion(job,editor.value);snapshot=recovered||discussionScope(editor.value);reviewSnapshot={text:job.original_text??job.text};refreshSnapshot();show(job,recovered,own);
  }catch(e){if(alive()&&own===serial)panel.querySelector('[data-question-status]').textContent=e.message}
 };
 history.onchange=()=>{if(history.value){put('-job',history.value);previous.hidden=false;previous.click()}};
 const historyQuery=historyContext||(exerciseKey?{exercise_key:exerciseKey}:null);
 if(historyQuery)api('/writing-questions/history?'+new URLSearchParams(historyQuery)).then(data=>{
  if(!alive()||!data.questions?.length)return;
  const saved=data.questions;
  if(!get('-job'))put('-job',saved[0].id);
  previous.hidden=false;history.hidden=false;
  history.innerHTML='<option value="">Saved questions · this task</option>'+saved.map(j=>`<option value="${esc(j.id)}">${esc((j.created||'').slice(0,10))} · ${esc(j.question)}</option>`).join('');
 }).catch(()=>{}); // Existing browser recovery remains available during an incomplete Sync.
 function dispose(){
  if(disposed)return;disposed=true;serial++;clearTimeout(poll);controller.abort();
  window.removeEventListener('hashchange',dispose);controls.remove();panel?.remove();
 }
 window.addEventListener('hashchange',dispose,{once:true});
 return {open,dispose};
}
