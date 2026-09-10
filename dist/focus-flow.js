import {criterionSummary} from './feedback.js';
import {neighbourContextHTML,argumentFlowHTML} from './argument-flow.js';
import {workingVersion} from './working-version.js';
// Progressive disclosure moves the original controls; it never copies learner text.
let currentFlow;
const focused=()=>document.body.classList.contains('focus-mode');
const element=(tag,cls)=>{const el=document.createElement(tag);if(cls)el.className=cls;return el};
function drawer(title,nodes,cls='focus-help-drawer'){
 const el=element('details',cls),summary=element('summary');summary.textContent=title;el.append(summary,...nodes.filter(Boolean));return el;
}
function group(nodes,steps){const el=element('div','focus-flow-group');el.dataset.focusSteps=steps;el.append(...nodes.filter(Boolean));return el}
function makeFlow(root,{key,title,steps,initial='read',editor,taskRoute=location.hash,keepInstructions=false}){
 currentFlow?.dispose();
 let stage;try{stage=localStorage.getItem('awl-focus-step-'+key)}catch{}
 if(!steps.some(s=>s.id===stage))stage=initial;
 const nav=element('section','focus-task-flow');nav.setAttribute('aria-label','Work on one step');
 const buttons=element('div','focus-step-buttons');buttons.setAttribute('role','group');buttons.setAttribute('aria-label','Writing steps');
 const cue=element('p','focus-step-cue');cue.setAttribute('role','status');
 for(const [i,s] of steps.entries()){
  const b=element('button','btn secondary');b.type='button';b.textContent=`${i+1} · ${s.label}`;b.dataset.focusStep=s.id;b.onclick=()=>select(s.id,true);buttons.append(b);
 }
 nav.append(buttons,cue);root.prepend(nav);
 let lastMode,lastStage;
 function apply(){
  if(!root.isConnected)return;
  const enabled=focused();if(lastMode===enabled&&lastStage===stage)return;lastMode=enabled;lastStage=stage;
  root.dataset.focusStep=stage;
  for(const g of root.querySelectorAll('[data-focus-steps]'))g.hidden=enabled&&!g.dataset.focusSteps.split(' ').includes(stage);
  for(const d of root.querySelectorAll('.focus-task-instructions'))d.open=!enabled||stage==='read'||(keepInstructions&&stage==='write');
  for(const d of root.querySelectorAll('.focus-normal-open'))d.open=!enabled;
  const step=steps.find(s=>s.id===stage);cue.textContent=step.cue;
  for(const b of buttons.children)b.setAttribute('aria-pressed',String(b.dataset.focusStep===stage));
 }
 function publish(){window.dispatchEvent(new CustomEvent('awl-focus-context',{detail:{goal:steps.find(s=>s.id===stage).goal||title,route:taskRoute}}))}
 function select(id,moveFocus=false){
  if(!steps.some(s=>s.id===id)||!root.isConnected)return;
  stage=id;try{localStorage.setItem('awl-focus-step-'+key,stage)}catch{}apply();publish();
  if(moveFocus&&focused()){
   const target=stage==='write'?root.querySelector(editor):buttons.querySelector(`[data-focus-step="${stage}"]`);
   target?.focus({preventScroll:true});nav.style.scrollMarginTop=((document.querySelector('#focus-work')?.offsetHeight||110)+24)+'px';nav.scrollIntoView({block:'start',behavior:'instant'});
  }
 }
 const onMode=()=>apply();window.addEventListener('awl-focus-mode',onMode);
 currentFlow={select,apply,nav,markReview:label=>{const b=buttons.querySelector('[data-focus-step="review"]');if(b)b.textContent=`3 · ${steps.find(s=>s.id==='review').label}${label?' · '+label:''}`},dispose:()=>window.removeEventListener('awl-focus-mode',onMode)};
 apply();publish();return currentFlow;
}
export function mountPracticeFocus(e,context){
 const root=document.querySelector('.exercise-body');if(!root)return;
 const $=s=>root.querySelector(s),all=[...root.children];
 const prompt=$('.prompt'),support=$('.learning-support[aria-label]');
 const helpNodes=[support,...all.filter(x=>x.matches('.criteria-guide,.outline-panel'))];
 const answerLabel=$('.editor-label'),submit=$('.submit-bar');
 const first=all.indexOf(answerLabel),last=all.indexOf(submit);
 const writing=group(all.slice(first,last+1),context.closed?'write':'write review');
 // Settings and optional revision reasons remain available without competing with the answer.
 const depth=writing.querySelector('.review-depth'),reason=writing.querySelector('#reason')?.closest('details'),saveOnly=writing.querySelector('#save-only');
 const options=drawer('Saving and tutor options',[reason,depth,saveOnly],'practice-options');submit.before(options);
 const supplied=all.filter(x=>x.matches('[aria-label="Supplied sentence parts"],[aria-label="Word bank"],[aria-label="Answer options"]'));
 writing.prepend(...supplied);
 const hint=$('#hint')?.parentElement,unlock=$('#example-unlock'),assistance=$('#assistance');
 const help=drawer('Help: steps, terms, hints & an example',[...helpNodes,hint,unlock,assistance]);help.id='focus-practice-help';
 // Opening a hint must also reveal the result when the help drawer was closed.
 help.addEventListener('click',event=>{if(event.target.closest('#hint,#show-example,#cross-domain-example'))help.open=true});
 const feedback=group([$('#tutor-feedback')],'write review');
 const review=group([$('#answer-feedback'),$('#next-exercise-area'),...(context.closed?[feedback]:[]),$('#writing-completion-review'),$('#attempt-history'),$('#module-progress'),$('.export-actions')],'review');
 let workspace;
 if(!context.closed){
  workspace=element('div','practice-revision-workspace');writing.classList.add('practice-draft-pane');feedback.classList.add('practice-feedback-pane');
  const notice=element('p','review-version-note');notice.id='review-version-note';writing.prepend(notice);
  workspace.append(writing,feedback);
 }
 const empty=element('p','focus-review-empty');empty.textContent='Save an answer to get feedback, or open your saved attempts below.';review.prepend(empty);
 const instructions=drawer('Task instructions and supplied facts',[prompt],'focus-task-instructions');
 const readNext=group([],'read');readNext.classList.add('focus-only');
 const next=element('button','btn');next.type='button';next.textContent='I understand the task · write my answer';readNext.append(next);
 const revise=element('button','btn secondary focus-only');revise.type='button';revise.textContent='Return to my answer';review.append(revise);
 const head=all.filter(x=>x.matches('.paper-practice-link,.paper-practice-return,.card-label,h2'));
 root.replaceChildren(...head,instructions,readNext,workspace||writing,help,review);
 const initial=context.closed||context.session.attempts.length||document.querySelector('#answer')?.value?'write':'read';
 const flow=makeFlow(root,{key:e.key,title:e.title,initial,editor:'#answer',keepInstructions:context.closed,steps:[
  {id:'read',label:'Understand',cue:'Read the task. Open a term or example only if it helps.',goal:'Understand one task: '+e.title},
  {id:'write',label:'Write',cue:context.closed?'Give one answer, then check it.':'Write one attempt. Save it when you are ready for feedback.',goal:'Write one answer: '+e.title},
  {id:'review',label:context.closed?'Review':'Review & revise',cue:context.closed?'Use the feedback to choose one next change.':'Your answer stays editable. Use the first feedback now; the second reading checks the submitted version.',goal:'Review one answer: '+e.title}
 ]});
 next.onclick=()=>flow.select('write',true);revise.onclick=()=>flow.select('write',true);
 root.querySelector('#bridge-use')?.addEventListener('click',()=>{if($('#answer').value.trim())flow.select('write',true)});
 const ready=()=>{empty.hidden=!!context.session.attempts.length||!!$('#answer-feedback')?.textContent.trim();};ready();
 const observer=new MutationObserver(ready);observer.observe(review,{childList:true,subtree:true,characterData:true});
 const dispose=flow.dispose;flow.dispose=()=>{dispose();observer.disconnect()};
 flow.syncReview=job=>{
  if(workspace){workspace.classList.toggle('has-review',!!job);workspace.querySelector('#review-version-note').hidden=!job;}
  if(job)flow.markReview(job.status==='complete'?'ready':job.result?'first ready':job.status==='queued'?'queued':'reading');
 };
 context.focusFlow=flow;flow.syncReview(context.reviewJob);return flow;
}
export function mountWiseFocus(n,p,context=null,esc=String){
 const root=document.querySelector('#wb-stage'),editor=root?.querySelector('.wb-editor');if(!editor)return;
 const $=s=>root.querySelector(s),original=[...editor.children];
 const support=$('#wise-node-support'),brief=$('.wb-brief'),plan=$('.wb-plan-fields');
 const sourceHelp=drawer('Teaching help, idea cards & discussion directions',[brief,support]);sourceHelp.id='focus-wise-help';
 const helpLabel=element('p','text-role teaching');helpLabel.textContent='Hints and examples help you think. They are not your manuscript text.';sourceHelp.insertBefore(helpLabel,brief);
 const optionalPlan=drawer('Reason and handover, when needed',[plan.querySelector('[data-plan="bridge"]')?.closest('label'),plan.querySelector('[data-plan="handover"]')?.closest('label')],'focus-plan-extra');
 plan.querySelector('[data-plan="contribution"]')?.closest('label').after(optionalPlan);
 const planGroup=group([plan],'plan');
 const freshStart=original.indexOf($('.wb-prose-label')),freshEnd=original.findIndex(x=>x.querySelector('#wb-select-version'));
 const draftNodes=original.slice(freshStart,freshEnd+1);
 const writing=group(draftNodes,'write');
 const notes=$('.wise-scratchpad');writing.prepend(notes);
 const selected=$('.wb-selected-version');let fresh;
 if(p.selected[n.id]?.document_id){
  fresh=drawer('Use a separate working draft instead',[...writing.children],'focus-fresh-draft');writing.append(selected,fresh);
 }else if(selected){selected.open=false;}
 const reviewActions=original.filter(x=>x.classList.contains('actions')&&x.querySelector('a[href^="#practice/"]'));
 const readLink=original.find(x=>x.tagName==='A'&&x.getAttribute('href')?.startsWith('#paper/read-'));
 const other=original.find(x=>x.tagName==='DETAILS'&&x.querySelector('.target-activities'));
 const preview=element('div','focus-wise-preview focus-only');
 const heading=element('h3');heading.textContent='Read the text you are working on';
 const prose=element('p','prose'),status=element('p','tiny');preview.append(heading,status,prose);
 const review=group([preview,...reviewActions,$('#wb-draft-marks'),...(!p.selected[n.id]?.document_id?[selected]:[]),readLink,other],'review');
 const saveControls=element('div','actions focus-only'),save=element('button','btn'),choose=element('button','btn secondary'),saveStatus=element('p','tiny focus-only');
 save.textContent='Save this editor version';choose.textContent='Choose manuscript version';saveControls.append(save,choose);preview.after(saveControls,saveStatus);
 save.onclick=()=>$('#wb-save-draft').click();choose.onclick=()=>$('#wb-select-version').click();
 const syncSaving=()=>{const disabled=$('#wb-save-draft').disabled||!$('#wb-draft').value.trim(),noVersions=$('#wb-select-version').disabled,text=$('#wb-draft-status').textContent;if(save.disabled!==disabled)save.disabled=disabled;if(choose.disabled!==noVersions)choose.disabled=noVersions;if(saveStatus.textContent!==text)saveStatus.textContent=text};
 const saveObserver=new MutationObserver(syncSaving);saveObserver.observe(editor,{childList:true,subtree:true,attributes:true,attributeFilter:['disabled'],characterData:true});
 const handover=element('p','focus-only tiny');handover.textContent='Read it aloud if that helps. Does each sentence support the paragraph’s job?';review.prepend(handover);
 const next=element('button','btn focus-only');next.textContent='Continue to my text';planGroup.append(next);
 const reviewButton=element('button','btn secondary focus-only');reviewButton.textContent='Read & choose my next step';writing.append(reviewButton);
 const editButton=element('button','btn secondary focus-only');editButton.textContent='Return to writing';review.append(editButton);
 const cue=element('div','focus-wise-job focus-only');cue.innerHTML='<small>Argument goal · planning guidance</small><strong></strong><p></p>';cue.querySelector('strong').textContent=n.purpose;cue.querySelector('p').textContent='Suggested check: '+n.boundary;
 const updateCheck=()=>{if(support.dataset.firstCheck)cue.querySelector('p').textContent='Suggested check: '+support.dataset.firstCheck};updateCheck();
 const checkObserver=new MutationObserver(updateCheck);checkObserver.observe(support,{attributes:true,attributeFilter:['data-first-check']});
 const orientation=element('details','wise-text-key');orientation.innerHTML='<summary>What is a hint, a source, or my text?</summary><dl><dt>Original manuscript</dt><dd>An excerpt from your uploaded PDF, with a file and page reference. It stays unchanged.</dd><dt>Archived idea card</dt><dd>Earlier notes or analysis, possibly written with an LLM. A card is not automatically agreed manuscript prose.</dd><dt>Teaching help</dt><dd>Hints, argument prompts and examples. Use the idea if helpful; they are not text you must copy.</dd><dt>My working copy / draft</dt><dd>The field you edit. Saving keeps a version; selecting places that version in WISE.</dd><dt>Selected for WISE</dt><dd>The saved text included when you read or export the manuscript. Later edits need a new selection.</dd></dl>';
 const sourceStart=element('div','wise-source-start');sourceStart.innerHTML='<p class="text-role source">2 · Decide how to write this move</p><p>Keep wording that already does the job. Adapt a passage if only its connection needs work. Combine selected blocks if the needed ideas are scattered. Write new prose if the argument is missing.</p>';
 const sourceLink=element('a','btn secondary');sourceLink.href='#revision/'+n.id;sourceLink.textContent='Find existing text for this argument';sourceStart.append(sourceLink);planGroup.prepend(sourceStart);if(context){const orientation=element('div','wise-argument-context');orientation.innerHTML=argumentFlowHTML(context,esc);planGroup.prepend(orientation);}
 const workingNote=element('p','text-role working');workingNote.textContent=p.selected[n.id]?.document_id?'Your selected passage is below. “Edit a copy” opens its original and editable text together.':'You are editing a separate working draft below. The uploaded manuscript remains in “Find my original manuscript passage”.';writing.prepend(workingNote);
 const editSelected=element('a','btn secondary');editSelected.textContent='Edit a copy of this selected passage';editSelected.href='#revision/'+n.id+'?reuse='+p.selected[n.id]?.id;preview.append(editSelected);
 const neighbours=element('div','wise-writing-context');if(context)neighbours.innerHTML=neighbourContextHTML(context,esc);
 const sheets=element('div','wise-writing-sheets');const proseSheet=element('div','wise-prose-sheet');proseSheet.append(...writing.children);sheets.append(notes,proseSheet);writing.append(sheets);
 const polish=element('details','wise-polish-guide');polish.innerHTML='<summary>From rough draft to polished paragraph</summary><ol><li>Keep your rough ideas in notes; write sentences in My paragraph text.</li><li>Check the meaning and the connection to nearby arguments first. Keep what already works.</li><li>Review with the tutor, choose one change, and practise one suggested skill if useful. Use Word help for a small phrase.</li><li>Read your revision in context, save it and choose the version for WISE.</li></ol><a href="/api/guides/draft-to-paper" target="_blank">Read the guide and an I-01 example</a>';
 editor.replaceChildren(neighbours,cue,orientation,polish,planGroup,writing,sourceHelp,review);
 const flow=makeFlow(root,{key:'wise-'+n.id,title:n.title,initial:'plan',editor:'#wb-draft',steps:[
  {id:'plan',label:'Understand the argument',cue:'First see what comes before and next. Then find text to keep, adapt or combine—or write a new draft.',goal:'WISE '+n.id+': '+n.purpose},
  {id:'write',label:'Work on my text',cue:'Change one passage. A teaching hint is optional; it does not belong in your draft automatically.',goal:'Work on one passage in WISE '+n.id},
  {id:'review',label:'Read & next step',cue:'Check meaning first. Save your version before selecting it for the paper.',goal:'Read one passage in WISE '+n.id}
 ]});
 if(new URLSearchParams(location.hash.split('?')[1]||'').get('write')==='new'){if(fresh)fresh.open=true;flow.select('write');}
 const updatePreview=()=>{const view=workingVersion(p.selected[n.id],$('#wb-draft')?.value,!!fresh?.open);prose.textContent=view.text||'There is no working draft yet. Return to writing or find an existing passage.';status.textContent=view.label;saveControls.hidden=!view.editable;saveStatus.hidden=!view.editable;editSelected.hidden=view.editable;for(const links of reviewActions)links.hidden=!view.editable;};
 next.onclick=()=>flow.select('write',true);reviewButton.onclick=()=>{updatePreview();flow.select('review',true)};editButton.onclick=()=>flow.select('write',true);
 $('#wb-draft')?.addEventListener('input',updatePreview);updatePreview();
 fresh?.addEventListener('toggle',updatePreview);
 syncSaving();const dispose=flow.dispose;flow.dispose=()=>{dispose();saveObserver.disconnect();checkObserver.disconnect()};
 // Read-step button also refreshes the preview without replacing or saving prose.
 flow.nav.addEventListener('click',updatePreview);
 return flow;
}
export function foldFeedbackForFocus(area,result){
 const box=area.querySelector('.tutor-box');if(!box)return;
 for(const [prefix,title] of [['What is covered',criterionSummary(result)]]){
  const h=[...box.children].find(x=>x.tagName==='H3'&&x.textContent.startsWith(prefix));if(!h)continue;
  const nodes=[];let next=h.nextElementSibling;while(next&&next.tagName!=='H3'){nodes.push(next);next=next.nextElementSibling}
  const d=drawer(title,nodes,'focus-normal-open feedback-fold');d.open=!focused();h.replaceWith(d);
 }
}
