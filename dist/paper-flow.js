export const paperRoute=(paper,card)=>'#papers/'+encodeURIComponent(paper)+(card?'?card='+encodeURIComponent(card):'');
export function flowNeighbours(plan,id){
 const args=plan.nodes.filter(n=>n.type==='argument'),i=args.findIndex(n=>n.id===id);
 return {before:i>0?args[i-1]:null,after:i>=0?args[i+1]||null:null,index:i,total:args.length};
}
export function sectionFor(plan,id){
 let n=plan.nodes.find(n=>n.id===id),seen=new Set();
 while(n?.parent_id&&!seen.has(n.id)){seen.add(n.id);n=plan.nodes.find(p=>p.id===n.parent_id)||n;}
 return n?.id||plan.nodes.find(n=>n.type==='section')?.id;
}
const stateName=n=>n.writing_status==='complete'?'Complete':n.fields?.['Manuscript prose']?.trim()?'Draft saved':'To write';
export function mapHTML(plan,current,section,esc){
 const roots=plan.nodes.filter(n=>!n.parent_id),scope=section||sectionFor(plan,current),route=id=>paperRoute(plan.id,id);
 const draw=parent=>plan.nodes.filter(n=>n.parent_id===parent).map(n=>n.type==='argument'?`<a class="paper-map-node ${n.id===current?'current':''}" href="${route(n.id)}" ${n.id===current?'aria-current="page"':''}><small>${esc(stateName(n))}${n.id===current?' · You are here':''}</small><strong>${esc(n.title)}</strong><span>${esc(n.fields.Purpose||'')}</span></a>`:`<section class="paper-map-group"><h3><a href="${route(n.id)}">${esc(n.title)}</a></h3><div class="paper-map-row">${draw(n.id)}</div></section>`).join('');
 const selected=plan.nodes.find(n=>n.id===scope);
 return `<p>Choose a box to open that part. The highlighted box is where you are writing. Follow the boxes in reading order.</p><nav class="paper-map-tabs" aria-label="Choose a paper section">${roots.map(n=>`<button class="btn ${n.id===scope?'':'secondary'}" data-flow-section="${esc(n.id)}">${esc(n.title)}</button>`).join('')}</nav><h3>${esc(selected?.title||plan.title)}</h3><div class="paper-map-row">${selected?.type==='argument'?`<a class="paper-map-node" href="${route(selected.id)}">${esc(selected.title)}</a>`:draw(scope)}</div>`;
}
export function previousHTML(note,esc){
 if(!note)return '<p>This is the first argument in the paper.</p>';
 return `<h3>${esc(note.title)}</h3><p><strong>Purpose:</strong> ${esc(note.fields.Purpose||'No purpose recorded.')}</p><h4>Current manuscript · read only here</h4>${note.fields['Manuscript prose']?.trim()?`<div class="paper-previous-prose">${esc(note.fields['Manuscript prose'])}</div>`:'<p>No manuscript prose has been saved for this argument yet.</p>'}<details><summary>Its argument notes</summary><div class="paper-previous-prose">${esc(note.fields['Notes and bullet points']||'No notes recorded.')}</div></details>`;
}
export function locationHTML(note,esc){return `<details class="paper-save-location"><summary>Where this is saved in Obsidian</summary><p><strong>${esc(note.title)}</strong></p><p>This is the live manuscript file used by both the Lab and Obsidian.</p><code>${esc(note.vault_path||note.path)}</code><div class="actions"><a class="btn secondary" href="${esc(note.uri)}">Open this exact note in Obsidian</a><button type="button" class="btn quiet" id="copy-paper-path">Copy file path</button></div><p class="tiny" id="copy-paper-path-status"></p></details>`;}
export function createPaperFlowUI({esc,modal,toast}){
 const $=s=>document.querySelector(s);
 function map(plan,current,section,save=async()=>{}){
  modal('Paper map',mapHTML(plan,current,section,esc));$('#modal').classList.add('paper-map-dialog');
  $('#modal').addEventListener('close',()=>$('#modal').classList.remove('paper-map-dialog'),{once:true});
  document.querySelectorAll('[data-flow-section]').forEach(b=>b.onclick=()=>map(plan,current,b.dataset.flowSection,save));
  document.querySelectorAll('#modal .paper-map-node,#modal .paper-map-group h3 a').forEach(a=>a.onclick=async event=>{event.preventDefault();try{await save();$('#modal').close();location.hash=a.getAttribute('href')}catch(e){toast(e.message)}});
 }
 function previous(plan,current,save=async()=>{}){
  const p=flowNeighbours(plan,current).before;
  modal('Previous argument',previousHTML(p,esc)+(p?`<p><a class="btn secondary" id="open-previous-argument" href="${paperRoute(plan.id,p.id)}">Open this argument for editing</a></p>`:''));
  if($('#open-previous-argument'))$('#open-previous-argument').onclick=async event=>{event.preventDefault();try{await save();$('#modal').close();location.hash=paperRoute(plan.id,p.id)}catch(e){toast(e.message)}};
 }
 function controls(plan,note){const f=flowNeighbours(plan,note.id);return `<nav class="paper-flow-controls" aria-label="Move through your paper"><button type="button" class="btn secondary" id="paper-previous" ${!f.before?'disabled':''}>← Read previous argument</button><button type="button" class="btn secondary" id="paper-map">Paper map</button>${f.after?`<button type="button" class="btn" id="paper-next">Next argument →<small>${esc(f.after.title)}</small></button>`:`<a class="btn secondary" href="${paperRoute(plan.id)}">Whole paper outline</a>`}</nav>`;}
 function bind(plan,note,save){
  if($('#paper-map'))$('#paper-map').onclick=()=>map(plan,note.id,undefined,save);
  if($('#paper-previous'))$('#paper-previous').onclick=()=>previous(plan,note.id,save);
  if($('#paper-next'))$('#paper-next').onclick=async()=>{try{await save();location.hash=paperRoute(plan.id,flowNeighbours(plan,note.id).after.id)}catch(e){toast(e.message)}};
  if($('#copy-paper-path'))$('#copy-paper-path').onclick=async()=>{try{await navigator.clipboard.writeText(note.path);$('#copy-paper-path-status').textContent='File path copied.'}catch{$('#copy-paper-path-status').textContent='Select and copy the path shown above.'}};
 }
 return {map,previous,controls,bind};
}
