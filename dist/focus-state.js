// Clock arithmetic is independent of rendering and browser timer throttling.
export const remaining=(s,now=Date.now())=>s?.phase==='running'?Math.max(0,s.endAt-now):Math.max(0,s?.remaining||0);
export function startFocus(minutes,goal,route,now=Date.now(),id=crypto.randomUUID()) {
 return {id,minutes,goal,route,phase:'running',started:new Date(now).toISOString(),endAt:now+minutes*60000,remaining:minutes*60000,parked:'',next_action:''};
}
export function pauseFocus(s,now=Date.now()){return {...s,remaining:remaining(s,now),phase:'paused'}}
export function resumeFocus(s,now=Date.now()){return {...s,phase:'running',endAt:now+s.remaining}}
export function finishFocus(s,outcome,now=Date.now()){
 return {id:s.id,minutes:s.minutes,goal:s.goal,route:s.route,started:s.started,finished:new Date(outcome==='interval_elapsed'?s.endAt:now).toISOString(),parked:s.parked||'',next_action:s.next_action||'',outcome};
}
export function clockDisplay(s,now=Date.now()){
 const idle=!s||s.phase==='finished',ms=idle?25*60000:remaining(s,now),seconds=Math.ceil(ms/1000);
 const text=`${Math.floor(seconds/60).toString().padStart(2,'0')}:${(seconds%60).toString().padStart(2,'0')}`;
 return {text,fraction:idle?1:Math.max(0,Math.min(1,ms/(s.minutes*60000||1))),label:`${text} ${idle?'ready to start':s.phase==='paused'?'remaining, paused':s.phase==='wrapping'?'remaining, ready to wrap up':'remaining'}`};
}
