// The existing Papyr sync owns delivery and task completion. We only add notes.
export const plannerRoute = route => /^#(?:reading|papers|paper|practice|fiction|revision|section-writing)\/[A-Za-z0-9%_:@.?=&-]+$/.test(route || '') ? route : '';
export function createPlannerUI({api,esc,toast,modal}) {
 let context=null;
 const $=s=>document.querySelector(s);
 window.addEventListener('awl-focus-context',e=>{context=e.detail});
 async function open(detail={}) {
  const route=plannerRoute(detail.route||location.hash);
  const current=context?.route===route?context:null;
  const title=String(detail.title||current?.goal||$('#main h1')?.textContent||'').replace(/[\r\n]+/g,' ').slice(0,500);
  const source_path=detail.source_path||current?.source_path||'';
  const request_id=crypto.randomUUID();
  modal('Send to my Papyr planner',`<p>Choose one concrete next action. It will be saved as a task in your synced Obsidian vault.</p><p id="planner-loading" role="status">Checking the planner folder…</p><form id="planner-task-form" hidden><label class="field">My next action<input name="title" maxlength="500" required value="${esc(title)}" placeholder="e.g. Clarify the evidence in my chapter summary"></label><div class="reading-question-row"><label class="field">Plan for<input name="day" type="date" required></label><label class="field">Estimated Pomodoros · optional<input name="pomodoros" type="number" min="1" max="99" placeholder="No estimate"></label></div><p class="tiny">This is a plan, not completed focus time.</p>${route?'<p>A link back to this Writing Lab task will be included.</p>':''}${source_path?`<p class="tiny">Source note: ${esc(source_path)}</p>`:''}<button class="btn" type="submit">Add task to Obsidian</button><p id="planner-task-status" role="status"></p></form><div id="planner-receipt" hidden></div>`);
  const form=$('#planner-task-form');
  try {
   const status=await api('/planner');if(!form.isConnected)return;
   if(!status.enabled){$('#planner-loading').innerHTML='Choose your Obsidian vault in <a href="#papers">Papers</a> first.';return}
   $('#planner-loading').textContent='Tasks are saved in '+status.folder+'/YYYY-MM-DD.md.';
   form.hidden=false;form.elements.day.value=status.today;
   form.onsubmit=async event=>{
    event.preventDefault();const button=form.querySelector('button[type=submit]');button.disabled=true;
    const payload={request_id,title:form.elements.title.value,day:form.elements.day.value,pomodoros:form.elements.pomodoros.value?Number(form.elements.pomodoros.value):0,route,source_path};
    try {
     const result=await api('/planner/tasks',payload);if(!form.isConnected){toast('Task saved to Obsidian. Run your Papyr sync to transfer it.');return}
     form.hidden=true;const receipt=$('#planner-receipt');receipt.hidden=false;receipt.innerHTML=`<div class="alert"><strong>${result.already_saved?'This task is already in your planner.':'Task saved to Obsidian.'}</strong><p>${esc(result.path)}</p><a class="btn secondary" href="${esc(result.uri)}">Open my planner note ↗</a></div><p>${esc(result.sync_help)}</p><p class="tiny">On Windows, let Obsidian Sync finish. Then use the existing Papyr sync on your Mac.</p>`;
    }catch(error){if(form.isConnected){$('#planner-task-status').textContent=error.message;button.disabled=false}}
   };
  } catch(error){if(form.isConnected)$('#planner-loading').textContent=error.message}
 }
 $('#send-to-planner').onclick=()=>open();
 window.addEventListener('awl-planner-request',event=>open(event.detail||{}));
 return {open};
}
