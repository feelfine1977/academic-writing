import {paperRoute,createPaperFlowUI,locationHTML} from './paper-flow.js';
export function createPaperReviewUI({api,esc,modal,toast,submit,isActive}){
 const flow=createPaperFlowUI({esc,modal,toast}),$=s=>document.querySelector(s);
 async function mount(c){
  const e=c.e,plan=c.workspacePlan;if(!plan)return;
  const note=await api(`/workspace/papers/${plan.id}/cards/${e.workspace_card_id}`);if(!isActive(c))return;
  const back=paperRoute(plan.id,note.id);
  $('.exercise-body').insertAdjacentHTML('afterbegin',`<section class="paper-practice-return"><a id="paper-review-back" href="${back}">← Return to my argument</a><p><strong>${esc(note.title)}</strong></p><p>Saved revisions update this manuscript card in Obsidian. Earlier versions remain in the history.</p>${flow.controls(plan,note)}${locationHTML(note,esc)}</section>`);
  $('#answer-feedback').insertAdjacentHTML('afterend',`<section id="writing-completion-review" class="paper-review-completion"><h3>Keep this version in my paper</h3><p>Save the current draft, or mark it complete when you are happy with it. Completion keeps you in this paper.</p><div class="actions"><button type="button" class="btn secondary" id="paper-review-save">Save draft & return</button><button type="button" class="btn" id="paper-review-complete">Complete & return to argument</button></div><p id="paper-review-save-status" role="status"></p></section>`);
  const persist=async(complete=false)=>{
   if(c.saving)throw new Error('A save is in progress. Please wait for it to finish.');
   if(!$('#answer').value.trim())throw new Error('Write your manuscript text first.');
   const submittedText=$('#answer').value;
   let latest=c.session.attempts.at(-1);
   if(!latest||latest.text!==$('#answer').value){const r=await submit(false);if(!r)throw new Error('The draft could not be saved. Your text stays in the editor.');if(r.paper_save_error)throw new Error(r.paper_save_error);latest=c.session.attempts.at(-1);}
   if(!isActive(c)||$('#answer').value!==submittedText)throw new Error('You edited the draft while it was saving. Your newer text is still here; save it before continuing.');
   const result=await api(`/workspace/papers/${plan.id}/cards/${note.id}/apply-attempt`,{attempt_id:latest.id,complete});
   if(result.conflict)throw new Error('Compare the competing manuscript versions before continuing.');
   if(!isActive(c)||$('#answer').value!==submittedText)throw new Error('You edited the draft while it was saving. Your newer text is still here; save it before continuing.');
   return result;
  };
  flow.bind(plan,note,()=>persist());
  $('#paper-review-back').onclick=async event=>{event.preventDefault();try{await persist();location.hash=back}catch(e){toast(e.message)}};
  for(const [id,complete] of [['paper-review-save',false],['paper-review-complete',true]])$('#'+id).onclick=async()=>{
   const b=$('#'+id);b.disabled=true;$('#paper-review-save-status').textContent='Saving to your manuscript…';
   try{await persist(complete);try{localStorage.removeItem(c.cache)}catch{}location.hash=back;toast(complete?'Argument saved and marked complete.':'Draft saved to your argument.');}
   catch(e){if($('#paper-review-save-status'))$('#paper-review-save-status').textContent=e.message;}
   finally{if(b.isConnected)b.disabled=false;}
  };
 }
 return {mount};
}
