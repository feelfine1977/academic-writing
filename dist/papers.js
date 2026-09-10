import {createPaperSourcesUI} from './paper-sources.js';
export function createPapersUI({api,esc,heading,modal,toast,isCurrent,refresh}){
 let active=null;
 const sourcesUI=createPaperSourcesUI({api,esc,modal,toast});
 const route=(paper,card)=>'#papers/'+encodeURIComponent(paper)+(card?'?card='+encodeURIComponent(card):'');
 const getCache=key=>{try{return JSON.parse(localStorage.getItem(key))}catch{return null}};
 const putCache=(key,value)=>{try{value?localStorage.setItem(key,JSON.stringify(value)):localStorage.removeItem(key);return true}catch{return false}};
 const $=s=>document.querySelector(s);
 function status(c,message,error=false){if(active===c&&$('#paper-save-status')){$('#paper-save-status').textContent=message;$('#paper-save-status').classList.toggle('error',error)}}
 async function save(c=active){
  if(!c)return;
  if(c.saving){await c.pending;return save(c)}
  if(c.blocked||!Object.keys(c.dirty).length)return;
  c.saving=true;c.pending=new Promise(resolve=>c.finishSave=resolve);clearTimeout(c.timer);const sent={...c.dirty};status(c,'Saving to your vault…');
  try{
   const result=await api(`/workspace/papers/${c.paper}/notes/${c.note.id}`,{base_hash:c.note.hash,fields:sent},'PATCH');
   c.note={...c.note,...result};
   for(const [k,v] of Object.entries(sent))if(c.dirty[k]===v)delete c.dirty[k];
   if(Object.keys(c.dirty).length)putCache(c.cache,{base_hash:c.note.hash,fields:c.dirty});else putCache(c.cache,null);
   status(c,result.conflict?'Saved versions need comparison. Your draft is kept.':'Saved to your Obsidian vault · '+result.filename,result.conflict);
   if(result.conflict)c.blocked=true;
  }catch(error){c.blocked=true;status(c,error.message+' Your editor draft is kept; use Compare & recover.',true)}
  finally{c.saving=false;c.finishSave();if(!c.blocked&&Object.keys(c.dirty).length)c.timer=setTimeout(()=>save(c),200)}
 }
 async function leave(){const c=active;if(c){clearTimeout(c.timer);await save(c);while(!c.blocked&&Object.keys(c.dirty).length)await save(c)}if(active===c)active=null}
 function changed(c,name,value){
  c.dirty[name]=value;
  const kept=putCache(c.cache,{base_hash:c.note.hash,fields:c.dirty});
  status(c,c.blocked?'A version needs comparison. Your editor text is kept.':kept?'Draft kept in this browser · saving shortly…':'Browser recovery is unavailable. Keep this page open until the vault save succeeds.',!kept);
  clearTimeout(c.timer);c.timer=setTimeout(()=>save(c),700);
 }
 function field(name,value,{large=false,placeholder=''}={}){return `<label class="field paper-field">${esc(name)}<textarea data-paper-field="${esc(name)}" rows="${large?12:3}" ${large?'class="editor"':''} placeholder="${esc(placeholder)}">${esc(value||'')}</textarea></label>`}
 function tree(nodes,paper,parent=null,current=null){
  const children=nodes.filter(n=>n.parent_id===parent);if(!children.length)return '';
  return `<ul class="paper-outline-tree">${children.map(n=>`<li><a href="${route(paper,n.id)}" ${n.id===current?'aria-current="page"':''}><small>${esc(n.type)}</small><span>${esc(n.title)}</span>${n.type==='argument'&&n.fields['Manuscript prose']?.trim()?'<span class="paper-has-text" aria-label="Has prose">●</span>':''}</a>${tree(nodes,paper,n.id,current)}</li>`).join('')}</ul>`;
 }
 async function setup(){
  const state=await api('/workspace');
  modal('Choose your Obsidian vault',`<p>Select the local vault folder synced on this computer. Your Windows and Mac paths can differ.</p><label class="field">Vault folder path<input id="workspace-vault" value="${esc(state.available?state.vault:'')}" placeholder="C:\\Users\\you\\Documents\\My Vault"></label><p class="tiny">Choose the folder containing .obsidian. On Windows, Shift + right-click the folder → Copy as path.</p><button id="workspace-connect" class="btn">Use this vault</button><p id="workspace-connect-status" role="status"></p>`);
  $('#workspace-connect').onclick=async()=>{try{await api('/workspace/configure',{vault:$('#workspace-vault').value.trim().replace(/^"|"$/g,'')});$('#modal').close();location.hash='#papers';await render()}catch(e){$('#workspace-connect-status').textContent=e.message}};
 }
 async function openFolder(){
  modal('Open an Obsidian paper folder',`<p>Choose the folder named after your paper, inside the selected vault. It needs one root paper card containing the linked outline.</p><label class="field">Paper folder<input id="paper-existing-folder" placeholder="06_Academic_Writing_Lab/Papers/WISE"></label><p class="tiny">Sections, subsections and arguments retain their existing identities and readable filenames. The app does not create a second copy.</p><button class="btn" id="paper-open-folder">Open as a project</button><p id="paper-folder-status" role="status"></p>`);
  $('#paper-open-folder').onclick=async()=>{try{const p=await api('/workspace/open-folder',{folder:$('#paper-existing-folder').value});$('#modal').close();location.hash=route(p.id)}catch(e){$('#paper-folder-status').textContent=e.message}};
 }
 async function newPaper(){
  modal('Start a paper',`<label class="field">Paper title<input id="new-paper-title" placeholder="A readable name for your paper" maxlength="150"></label><label class="field">Outline, bullets or prose (optional)<textarea id="new-paper-outline" rows="10" placeholder="## Section: Introduction\n### Subsection: Motivation\n#### Argument: Why the problem matters\n- Your first idea\n### Manuscript prose\nYour existing text, if you have any."></textarea></label><label class="field">Or load an outline file<input type="file" id="new-paper-file" accept=".md,.txt"></label><p class="tiny">Sections and subsections group arguments. Empty cards are welcome. Use “### Manuscript prose” to distinguish actual text from notes.</p><button class="btn" id="create-paper">Create paper</button><p id="create-paper-status" role="status"></p>`);
  $('#new-paper-file').onchange=async e=>{if(e.target.files[0])$('#new-paper-outline').value=await e.target.files[0].text()};
  $('#create-paper').onclick=async()=>{const b=$('#create-paper');b.disabled=true;try{const p=await api('/workspace/papers',{title:$('#new-paper-title').value,outline:$('#new-paper-outline').value});$('#modal').close();location.hash=route(p.id)}catch(e){$('#create-paper-status').textContent=e.message;b.disabled=false}};
 }
 async function addCard(paper,nodes,parent){
  modal('Add to the argument outline',`<label class="field">Card title<input id="new-card-title" maxlength="150" placeholder="What this part should establish"></label><label class="field">Type<select id="new-card-kind"><option value="argument">Argument</option><option value="subsection">Subsection</option><option value="section">Section</option></select></label><label class="field">Inside<select id="new-card-parent"><option value="">Whole paper</option>${nodes.filter(n=>n.type!=='argument').map(n=>`<option value="${esc(n.id)}">${esc(n.type+' · '+n.title)}</option>`).join('')}</select></label><button class="btn" id="create-card">Add card</button><p id="create-card-status" role="status"></p>`);
  $('#new-card-parent').value=parent||'';
  $('#new-card-kind').onchange=()=>{if($('#new-card-kind').value==='section')$('#new-card-parent').value=''};
  $('#create-card').onclick=async()=>{try{const card=await api(`/workspace/papers/${paper}/cards`,{title:$('#new-card-title').value,kind:$('#new-card-kind').value,parent_id:$('#new-card-parent').value||null});$('#modal').close();location.hash=route(paper,card.id)}catch(e){$('#create-card-status').textContent=e.message}};
 }
 async function compare(c){
  await save(c);
  const latest=await api(`/workspace/papers/${c.paper}`+(c.note.id!==c.paper?`/cards/${c.note.id}`:''));
  const history=await api(`/workspace/papers/${c.paper}/notes/${c.note.id}/history`);
  const mine={...c.note.fields,...c.dirty};
  const show=fields=>Object.entries(fields).filter(([k,v])=>v).map(([k,v])=>`<h4>${esc(k)}</h4><p class="prose">${esc(v)}</p>`).join('');
  modal('Compare saved versions',`<div class="paper-compare"><section><h3>Current vault text</h3>${show(latest.fields)}</section><section><h3>My editor draft</h3>${show(mine)}</section></div><details><summary>Saved history (${history.length})</summary>${history.map(r=>`<details><summary>${esc(new Date(r.created).toLocaleString())} · ${esc(r.origin)}</summary>${show(r.fields)}</details>`).join('')}</details><p>Choose deliberately after reading both versions. History is retained.</p><div class="actions"><button class="btn secondary" id="recover-vault">Use current vault text</button><button class="btn" id="recover-mine">Save my displayed draft after comparing</button></div><p id="recovery-status" role="status"></p>`);
  $('#recover-vault').onclick=async()=>{try{if(latest.conflict)await api(`/workspace/papers/${c.paper}/notes/${c.note.id}`,{base_hash:latest.hash,fields:{},merge_heads:latest.heads.map(h=>h.id)},'PATCH');putCache(c.cache,null);c.dirty={};c.blocked=false;$('#modal').close();render(c.paper,undefined,c.note.id===c.paper?null:c.note.id)}catch(e){$('#recovery-status').textContent=e.message}};
  $('#recover-mine').onclick=async()=>{try{const fields=Object.fromEntries(Object.keys(c.dirty).map(k=>[k,mine[k]]));if(!Object.keys(fields).length)Object.assign(fields,Object.fromEntries(Object.entries(mine).filter(([k])=>c.allowed.includes(k))));await api(`/workspace/papers/${c.paper}/notes/${c.note.id}`,{base_hash:latest.hash,fields,...(latest.conflict?{merge_heads:latest.heads.map(h=>h.id)}:{})},'PATCH');putCache(c.cache,null);c.dirty={};$('#modal').close();render(c.paper,undefined,c.note.id===c.paper?null:c.note.id)}catch(e){$('#recovery-status').textContent=e.message}};
 }
 function mountEditor(c){
  const cached=getCache(c.cache);
  if(cached?.fields){c.dirty=cached.fields;c.blocked=cached.base_hash!==c.note.hash;for(const el of document.querySelectorAll('[data-paper-field]'))if(el.dataset.paperField in cached.fields)el.value=cached.fields[el.dataset.paperField];status(c,c.blocked?'Recovered editor text differs from the vault. Compare before saving.':'Recovered your unfinished editor draft.',c.blocked);if(!c.blocked)c.timer=setTimeout(()=>save(c),700)}
  if(c.note.conflict){c.blocked=true;status(c,'Competing saved versions need comparison. You can keep editing your local draft.',true)}
  document.querySelectorAll('[data-paper-field]').forEach(el=>el.addEventListener('input',()=>changed(c,el.dataset.paperField,el.value)));
  $('#paper-save-now').onclick=()=>{if(c.blocked)compare(c);else save(c)};
  $('#paper-compare').onclick=()=>compare(c);
 }
 async function render(id,serial,cardId){
  if(active)await leave();
  const current=()=>serial===undefined||isCurrent(serial);
  if(!id){
   const data=await api('/workspace');if(!current())return;
   const resume=getCache('awl-paper-resume');
   $('#main').innerHTML=heading('My papers','Your argument plan, notes and prose in Obsidian.')+`<div class="actions"><button class="btn" id="new-paper" ${!data.enabled?'disabled':''}>New paper</button><button class="btn secondary" id="open-paper-folder" ${!data.enabled?'disabled':''}>Open Obsidian paper folder</button><button class="btn secondary" id="sync-paper-learning" ${!data.enabled?'disabled':''}>Sync saved learning</button><button class="btn secondary" id="select-paper-vault">${data.enabled?'Change vault':'Choose Obsidian vault'}</button>${resume&&data.papers.some(p=>p.id===resume.paper)?`<a class="btn secondary" href="${route(resume.paper,resume.card)}">Resume writing</a>`:''}</div>${data.enabled?`<p class="tiny">${esc(data.vault)} · ${esc(data.folder)}</p><p class="tiny">${esc(data.sync)}</p>`:'<div class="card"><h2>One private writing folder on each computer</h2><p>Choose the Obsidian vault you already sync. Papers use readable names and linked section, subsection and argument cards.</p><p>On Windows, the local tutor can use your existing Ollama installation.</p></div>'}${data.issues.map(x=>`<div class="alert error">${esc(x)}</div>`).join('')}<div class="catalogue-grid">${data.papers.map(p=>`<a class="card catalogue-card" href="${route(p.id)}"><small>Paper</small><h2>${esc(p.title)}</h2><p>Open argument outline →</p></a>`).join('')}</div>`;
   $('#select-paper-vault').onclick=setup;$('#new-paper').onclick=newPaper;$('#open-paper-folder').onclick=openFolder;$('#sync-paper-learning').onclick=async()=>{const b=$('#sync-paper-learning');b.disabled=true;b.textContent='Syncing…';try{const r=await api('/workspace/sync',{});toast(r.message+(r.issues?.length?' '+r.issues[0]:''))}catch(e){toast(e.message)}finally{b.disabled=false;b.textContent='Sync saved learning'}};return;
  }
  const plan=await api('/workspace/papers/'+id);const note=cardId?await api(`/workspace/papers/${id}/cards/${cardId}`):plan;if(!current())return;
  putCache('awl-paper-resume',{paper:id,card:cardId});const allowed=cardId?['Purpose','Main message','Scope and boundaries','Notes and bullet points','Source mapping','Manuscript prose','Reasoning and decisions','Next step','Connection to the surrounding argument']:['Research question','Intended contribution','Agreed plan and open questions','Next writing session','Argument order'];
  const c={paper:id,note,allowed,cache:'awl-vault-draft-'+id+'-'+note.id,dirty:{},saving:false,blocked:false};active=c;
  const context=n=>n?`<a href="${route(id,n.id)}"><small>${esc(n.type)}</small><strong>${esc(n.title)}</strong><span>${esc(n.fields.Purpose||'Purpose not written yet.')}</span></a>`:'<span class="tiny">Boundary of this part</span>';
  $('#main').innerHTML=`<div class="paper-workspace-header"><div><a href="#papers">← My papers</a><h1>${esc(cardId?note.title:plan.title)}</h1><p>${cardId?`<a href="${route(id)}">${esc(plan.title)} · Whole argument</a>`:'Plan the argument, then develop one card at a time.'}</p></div><div class="actions"><a class="btn secondary" href="${esc(note.uri)}">Open in Obsidian</a><button class="btn secondary" id="add-paper-card">Add card</button><button class="btn secondary" id="paper-import-source">Import source</button><button class="btn secondary" id="paper-find-source">Find source passages</button></div></div><div class="paper-workspace-shell"><details class="paper-outline-nav" open><summary>Argument outline</summary>${tree(plan.nodes,id,null,cardId)}${plan.unplaced?.length?`<details><summary>Unplaced cards (${plan.unplaced.length})</summary><p>These cards are kept but have no outline link. Add their links under a suitable parent in Edit the linked outline.</p>${plan.unplaced.map(n=>`<p><a href="${esc(n.uri)}">${esc(n.title)}</a><code>${esc('[Argument: '+n.title+'](Cards/'+encodeURIComponent(n.filename)+')')}</code></p>`).join('')}</details>`:''}<a href="/api/workspace/papers/${id}/export" class="btn quiet">Download working manuscript</a></details><section class="card paper-writing-panel">${cardId?`<nav class="paper-neighbours" aria-label="Surrounding argument">${context(note.before)}<div><small>You are writing</small><strong>${esc(note.title)}</strong>${note.parent?`<a href="${route(id,note.parent.id)}">↑ ${esc(note.parent.title)}</a>`:''}</div>${context(note.after)}</nav>`:''}
   ${cardId?field('Purpose',note.fields.Purpose,{placeholder:'What should the reader understand after this argument?'})+ (note.type==='argument'?`<div class="paper-drafting-grid">${field('Notes and bullet points',note.fields['Notes and bullet points'],{placeholder:'Plan, questions and rough ideas…'})}${field('Manuscript prose',note.fields['Manuscript prose'],{large:true,placeholder:'Your actual text. Empty is fine while you plan.'})}</div><details><summary>Original passages and source mapping</summary>${field('Source mapping',note.fields['Source mapping'])}</details>`:field('Main message',note.fields['Main message'])+`<h3>Inside this ${esc(note.type)}</h3>${note.children.length?`<div class="paper-child-cards">${note.children.map(context).join('')}</div>`:'<p>This part can stay empty, or you can add its first card.</p>'}<details><summary>Planning notes and scope</summary>${field('Notes and bullet points',note.fields['Notes and bullet points'])}${field('Scope and boundaries',note.fields['Scope and boundaries'])}${field('Connection to the surrounding argument',note.fields['Connection to the surrounding argument'])}</details>`)+`<details><summary>My reasoning and decisions</summary>${field('Reasoning and decisions',note.fields['Reasoning and decisions'])}</details>${field('Next step',note.fields['Next step'],{placeholder:'One small action to resume…'})}`:
   `${field('Research question',plan.fields['Research question'])}${field('Intended contribution',plan.fields['Intended contribution'])}<h2>The argument at a glance</h2><div class="paper-child-cards">${plan.nodes.filter(n=>!n.parent_id).map(context).join('')}</div><details><summary>Edit the linked outline</summary><p class="tiny">Indent subsections and arguments under their parent. Keep each card link once. Move a whole group together.</p>${field('Argument order',plan.fields['Argument order'],{large:true})}</details><details><summary>Agreed plan and open questions</summary>${field('Agreed plan and open questions',plan.fields['Agreed plan and open questions'])}</details>${field('Next writing session',plan.fields['Next writing session'])}`}
   <div class="paper-save-bar"><p id="paper-save-status" role="status">Saved in your vault · ${esc(note.filename)}</p><button class="btn" id="paper-save-now">Save now</button><button class="btn secondary" id="paper-compare">Compare & recover</button>${note.type==='argument'?'<button class="btn secondary" id="paper-review-argument">Review or ask about my text</button>':''}</div><p class="tiny">${esc(plan.sync)} Your private notes remain outside the app’s source code.</p></section></div>`;
  $('#add-paper-card').onclick=()=>addCard(id,plan.nodes,note.type==='argument'?note.parent_id:cardId);
  mountEditor(c);
  if($('#paper-review-argument'))$('#paper-review-argument').onclick=async()=>{const b=$('#paper-review-argument');b.disabled=true;try{await save(c);if(c.blocked)throw new Error('Compare your saved versions before reviewing.');const r=await api(`/workspace/papers/${id}/cards/${cardId}/practice`,{});await refresh();location.hash='#practice/'+encodeURIComponent(r.exercise_key)+'?session='+encodeURIComponent(r.session_id)}catch(e){toast(e.message);b.disabled=false}};
  $('#paper-import-source').onclick=()=>sourcesUI.upload(id);
  $('#paper-find-source').onclick=()=>sourcesUI.browse(id,note.type==='argument'?text=>{const el=$('[data-paper-field="Source mapping"]');el.value=el.value.trim()+text;changed(c,'Source mapping',el.value)}:null);
  window.dispatchEvent(new CustomEvent('awl-focus-context',{detail:{goal:note.title,route:route(id,cardId)}}));
 }
 window.addEventListener('beforeunload',event=>{if(active&&(active.saving||Object.keys(active.dirty).length)){event.preventDefault();event.returnValue=''}});
 return {render,leave};
}
