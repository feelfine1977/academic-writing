// Lives outside the routed workspace: navigation must never hide a running tutor.
export function createActivityUI({api,esc,toast}) {
 const host=document.querySelector('#continue-work');
 const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}};
 const write=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value))}catch{}};
 let reviews=[],busy=false,timer=null,signature='',lastStates=new Map();
 function remember(e,session,from){
  const pins=read('awl-work-pins',[]).filter(p=>p.exercise_id!==e.key);
  pins.unshift({exercise_id:e.key,title:e.title,session_id:session.id,from,kind:e.workspace_paper_id?"paper-review":undefined,updated:Date.now()});
  write('awl-work-pins',pins.slice(0,5));draw();
 }
 function href(p){if(p.kind==='section-writing')return '#section-writing/'+encodeURIComponent(p.paper_id)+'?section='+encodeURIComponent(p.section_id);if(p.kind==='reading')return '#reading/'+encodeURIComponent(p.document_id);if(p.kind==='paper')return '#paper/'+encodeURIComponent(p.node_id);const q=new URLSearchParams({session:p.session_id});if(p.id)q.set('job',p.id);if(p.from||p.paper_node_id)q.set('from',p.from||p.paper_node_id);return '#practice/'+encodeURIComponent(p.exercise_id)+'?'+q}
 function draw(){
  const dismissed=new Set(read('awl-work-dismissed',[])),pins=read('awl-work-pins',[]);
  const jobs=reviews.filter(j=>!dismissed.has(j.id)||['queued','running'].includes(j.status));
  const pending=jobs.filter(j=>['queued','running'].includes(j.status));
  const recent=jobs.filter(j=>!['queued','running'].includes(j.status));
  const items=[...pending,...recent.slice(0,4),...pins.filter(p=>['paper','reading','section-writing'].includes(p.kind)||!jobs.some(j=>j.session_id===p.session_id))];
  const key=JSON.stringify(items);if(key===signature)return;signature=key;
  if(!items.length){host.hidden=true;return}host.hidden=false;
  const status=p=>p.kind==='section-writing'?'Resume section draft':p.kind==='reading'?'Resume reading note':p.kind==='paper'?'Return to earlier paper draft':p.preview_ready?'First feedback ready · checking':({running:'Tutor is reading',queued:'Waiting for tutor',complete:'Feedback ready',failed:'Review needs a retry',cancelled:'Review cancelled',interrupted:'Review interrupted · retry'}[p.status]||(p.kind==='paper-review'?'Resume paper review':'Resume exercise'));
  window.dispatchEvent(new CustomEvent('awl-activity-updated',{detail:items.slice(0,8).map(p=>({title:p.title,href:href(p),status:status(p)}))}));
  host.innerHTML=`<div class="continue-primary"><strong>Continue your work</strong><a href="${esc(href(items[0]))}">${esc(items[0].title)} <span class="tag">${esc(status(items[0]))}</span></a>${pins.find(p=>p.kind==='paper')?`<a class="continue-wise" href="${esc(href(pins.find(p=>p.kind==='paper')))}">↩ Earlier draft · ${esc(pins.find(p=>p.kind==='paper').node_id)}</a>`:''}</div><details><summary>All pinned work (${items.length})</summary><ul>${items.map(p=>`<li><a href="${esc(href(p))}"><strong>${esc(p.title)}</strong><small>${esc(status(p))}${p.created?' · '+esc(new Date(p.created).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})):''}</small></a>${!['queued','running'].includes(p.status)?`<button class="btn quiet" data-dismiss-work="${esc(p.id||p.exercise_id)}" aria-label="Unpin ${esc(p.title)}">Unpin</button>`:''}</li>`).join('')}</ul><p class="tiny">Saved answers stay in Learning → Saved answers after unpinning. Tutor reviews continue while you use other pages.</p></details>`;
  host.querySelectorAll('[data-dismiss-work]').forEach(b=>b.onclick=()=>{const id=b.dataset.dismissWork;write('awl-work-dismissed',[...dismissed,id].slice(-150));const job=reviews.find(j=>j.id===id);write('awl-work-pins',pins.filter(p=>p.exercise_id!==(job?.exercise_id||id)));signature='';draw()});
 }
 async function refresh(){
  if(busy)return;busy=true;clearTimeout(timer);
  try{const data=await api('/activity');reviews=data.reviews;
   for(const r of reviews){const previous=lastStates.get(r.id);if(previous&&['queued','running'].includes(previous)&&r.status==='complete'&&!document.body.classList.contains('focus-mode'))toast('Tutor feedback is ready: '+r.title+'. Open Continue your work.');lastStates.set(r.id,r.status)}
   draw();
  }catch{if(!host.hidden)host.dataset.offline='true'}finally{busy=false;timer=setTimeout(refresh,5000)}
 }
 window.addEventListener('awl-paper-open',event=>{const n=event.detail;if(!/^[A-Z]+-[A-Z0-9]+$/.test(n.id))return;const pins=read('awl-work-pins',[]).filter(p=>p.exercise_id!=='paper:'+n.id);pins.unshift({kind:'paper',exercise_id:'paper:'+n.id,node_id:n.id,title:n.title,updated:Date.now()});write('awl-work-pins',pins.slice(0,5));signature='';draw()});
 window.addEventListener('awl-reading-open',event=>{const n=event.detail;if(!/^[a-f0-9-]{36}$/.test(n.id))return;const pins=read('awl-work-pins',[]).filter(p=>p.exercise_id!=='reading:'+n.id);pins.unshift({kind:'reading',exercise_id:'reading:'+n.id,document_id:n.id,title:n.title,updated:Date.now()});write('awl-work-pins',pins.slice(0,5));signature='';draw()});
 window.addEventListener('awl-section-open',event=>{const n=event.detail;if(!/^[A-Za-z0-9_-]{1,100}$/.test(n.id||'')||!/^[A-Za-z0-9_-]{1,100}$/.test(n.paper_id||''))return;const key='section:'+n.paper_id+':'+n.id,pins=read('awl-work-pins',[]).filter(p=>p.exercise_id!==key);pins.unshift({kind:'section-writing',exercise_id:key,paper_id:n.paper_id,section_id:n.id,title:n.title,updated:Date.now()});write('awl-work-pins',pins.slice(0,5));signature='';draw()});
 window.addEventListener('storage',()=>{signature='';draw()});
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});
 return {remember,refresh};
}
