import {remaining,startFocus,pauseFocus,resumeFocus,finishFocus,clockDisplay} from './focus-state.js';
export function createFocusUI({api,esc,toast}) {
 const host=document.querySelector('#focus-work'),$=s=>host.querySelector(s);
 const read=(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch{return d}};
 const write=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch{toast('Browser storage unavailable. Keep this page open for the focus timer.')}};
 let state=read('awl-focus-clock',null),focus=read('awl-focus-view',false),task=null,syncing=false;
 let colour=read('awl-focus-colour','red'),recent=[];
 const persist=()=>write('awl-focus-clock',state);
 const safeRoute=r=>/^#(?:paper|papers|practice|revision)\/[A-Za-z0-9%_:@.?=&-]+$/.test(r||'')?r:'#today';
 const inProgress=()=>state&&['running','paused','wrapping'].includes(state.phase);
 function showRecent(){const list=$('#focus-recent-list');if(!list)return;list.innerHTML=recent.length?recent.map(p=>`<a href="${esc(safeRoute(p.href))}"><strong>${esc(p.title)}</strong><small>${esc(p.status)}</small></a>`).join(''):'<p>No recent work yet. Open one exercise or WISE paragraph.</p>';$('#focus-recent-count').textContent=recent.length?` (${recent.length})`:'';}
 function mode(){
  document.body.classList.toggle('focus-mode',focus);write('awl-focus-view',focus);
  $('#focus-view').textContent=focus?'Exit focus':'Focus view';$('#focus-view').setAttribute('aria-pressed',String(focus));
  window.dispatchEvent(new CustomEvent('awl-focus-mode',{detail:{enabled:focus}}));
 }
 async function sync(){
  if(syncing)return;syncing=true;
  try{for(const record of read('awl-focus-outbox',[])){await api('/focus/sessions',record);write('awl-focus-outbox',read('awl-focus-outbox',[]).filter(x=>x.id!==record.id))}if($('#focus-saved'))$('#focus-saved').textContent='Focus record saved on this Mac.'}
  catch{if($('#focus-saved'))$('#focus-saved').textContent='Record kept in this browser; retrying when the server is available.'}
  finally{syncing=false}
 }
 function finishRecord(){
  if(!inProgress())return;
  if(state.kind!=='break'){
   const record=finishFocus(state,state.wrapReason||'stopped_early');
   const outbox=read('awl-focus-outbox',[]);if(!outbox.some(x=>x.id===record.id))outbox.push(record);write('awl-focus-outbox',outbox);
  }
  state={...state,phase:'finished',remaining:0};persist();draw();sync();
 }
 function start(minutes,goal,route,kind='focus'){
  state={...startFocus(minutes,goal,safeRoute(route)),kind};persist();if(kind==='focus')focus=true;draw();
 }
 function wrap(reason){
  if(!state||!['running','paused'].includes(state.phase))return;
  state={...pauseFocus(state),phase:'wrapping',wrapReason:reason};persist();draw();
  // No dialog, sound, focus theft or automatic navigation when time elapses.
  if(reason==='stopped_early'){$('#focus-settings').open=true;$('#focus-next')?.focus()}
 }
 function noteFields(){return `<label class="field">Park a thought for later<textarea id="focus-parked" maxlength="3000" rows="2">${esc(state?.parked||'')}</textarea></label><label class="field">When I return, my next action is…<input id="focus-next" maxlength="1000" placeholder="e.g. check the reason linking these two sentences" value="${esc(state?.next_action||'')}"></label><p class="tiny">Notes stay in this browser until you finish and save this interval.</p>`}
 function draw(){
  const active=inProgress(),wrapping=state?.phase==='wrapping',finished=state?.phase==='finished',isBreak=state?.kind==='break';
  const goal=active?state.goal:task?.goal||state?.next_action||'Choose one exercise or writing task';
  const route=active?state.route:task?.route;
  host.dataset.colour=isBreak?'teal':colour;
  host.innerHTML=`<div class="focus-bar"><div class="focus-timepiece"><svg viewBox="0 0 80 80" aria-hidden="true"><circle class="clock-track" cx="40" cy="40" r="35"/><circle id="clock-ring" cx="40" cy="40" r="35" pathLength="100"/></svg><strong id="focus-clock" role="timer" aria-live="off" aria-label="Time remaining">25:00</strong></div><div class="focus-anchor"><span id="focus-status" role="status">${wrapping?'Time to wrap up':active?(isBreak?'Break':state.phase==='paused'?'Paused':'One task for now'):finished?'Interval saved':'Pomodoro · ready when you are'}</span><strong class="focus-goal">${esc(goal)}</strong>${route?`<a class="focus-return" href="${esc(safeRoute(route))}">${active?'Return to this task':'Current task'}</a>`:''}</div><div class="focus-controls">${active?(wrapping?'<button class="btn focus-primary" id="focus-break">Save & take 5 min break</button><button class="btn secondary" id="focus-more">Keep writing · 5 min</button>':`<button class="btn secondary" id="focus-pause">${state.phase==='paused'?'Resume':'Pause'}</button><button class="btn quiet" id="focus-stop">Wrap up</button>`):'<button class="btn focus-primary" id="focus-quick">Start 25 min</button><button class="btn secondary" id="focus-small">Small start · 10 min</button>'}<button class="btn quiet" id="focus-view"></button></div><details id="focus-settings"><summary>${active?'Notes & finish':'Timer options'}</summary><div class="focus-settings-inner">${active?noteFields()+`<button id="focus-finish" class="btn focus-primary">Finish & save interval</button>${wrapping?'<p class="tiny">Finish your sentence first. Nothing is submitted, marked complete or erased when time ends.</p>':''}`:`<label class="field">One concrete task<input id="focus-goal-input" maxlength="500" value="${esc(task?.goal||state?.next_action||'')}"></label><label class="field">Interval<select id="focus-minutes"><option value="25">25 minutes</option><option value="2">2 minutes · just begin</option><option value="10">10 minutes · small start</option><option value="15">15 minutes</option><option value="45">45 minutes</option><option value="50">50 minutes</option></select></label><button id="focus-start" class="btn focus-primary">Start this interval</button>${finished?'<p id="focus-saved" class="tiny" role="status"></p><button class="btn secondary" id="focus-break">Take a 5-minute break</button>':''}`}<label class="field">Clock colour<select id="focus-colour"><option value="red">Red</option><option value="blue">Quiet blue</option></select></label><p class="tiny">A timer is a cue, not a deadline or a learning score. Breaks are your choice.</p></div></details></div>`;
  $('#focus-view').onclick=()=>{focus=!focus;mode()};mode();
  $('#focus-colour').value=colour;$('#focus-colour').onchange=e=>{colour=e.target.value;write('awl-focus-colour',colour);host.dataset.colour=isBreak?'teal':colour};
  if(active){
   if($('#focus-pause'))$('#focus-pause').onclick=()=>{state=state.phase==='running'?pauseFocus(state):resumeFocus(state);persist();draw();$('#focus-pause')?.focus()};
   if($('#focus-stop'))$('#focus-stop').onclick=()=>wrap('stopped_early');
   $('#focus-parked').oninput=e=>{state.parked=e.target.value;persist()};$('#focus-next').oninput=e=>{state.next_action=e.target.value;persist()};
   $('#focus-finish').onclick=finishRecord;
   if($('#focus-more'))$('#focus-more').onclick=()=>{const old=state;finishRecord();start(5,old.goal,old.route);};
  }else{
   $('#focus-quick').onclick=()=>start(25,task?.goal||'One focused writing task',task?.route||location.hash);
   $('#focus-small').onclick=()=>start(10,task?.goal||'Make one small start',task?.route||location.hash);
   $('#focus-start').onclick=()=>start(Number($('#focus-minutes').value),$('#focus-goal-input').value,task?.route||location.hash);
  }
  if($('#focus-break'))$('#focus-break').onclick=()=>{const old=state;if(inProgress())finishRecord();start(5,'Break · move, stretch or rest your eyes',old?.route||location.hash,'break');};
  const recentMenu=document.createElement('details');recentMenu.id='focus-recent';recentMenu.innerHTML='<summary>Recent work<span id="focus-recent-count"></span></summary><div id="focus-recent-list" class="focus-settings-inner"></div>';$('.focus-bar').append(recentMenu);showRecent();tick();
 }
 function tick(){
  if(state?.phase==='running'&&remaining(state)<=0){
   if(state.kind==='break'){state={...state,phase:'finished',remaining:0};persist();draw();return}
   wrap('interval_elapsed');return;
  }
  const clock=clockDisplay(state);
  if($('#focus-clock')){$('#focus-clock').textContent=clock.text;$('#focus-clock').setAttribute('aria-label',clock.label)}
  $('#clock-ring')?.setAttribute('stroke-dasharray',`${clock.fraction*100} 100`);
 }
 window.addEventListener('storage',e=>{if(e.key==='awl-focus-clock'){state=read('awl-focus-clock',null);draw()}else if(e.key==='awl-focus-view'){focus=read('awl-focus-view',false);mode()}});
 window.addEventListener('awl-focus-context',e=>{task=e.detail;if(!inProgress())draw()});
 window.addEventListener('awl-activity-updated',e=>{recent=e.detail;showRecent()});
 window.addEventListener('awl-focus-request',e=>{task=e.detail;focus=true;draw();if(!inProgress()){$('#focus-settings').open=true;$('#focus-goal-input')?.focus()}else toast('Your interval stays linked to its original task. Use Return to this task to resume it.')});
 document.addEventListener('visibilitychange',()=>{if(!document.hidden){tick();sync()}});
 window.addEventListener('online',sync);setInterval(tick,1000);setInterval(sync,30000);draw();sync();
 return {sync};
}
