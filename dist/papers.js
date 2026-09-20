import {createPaperDeskUI} from './paper-desk.js';
import {createPaperFlowUI,flowNeighbours,locationHTML} from './paper-flow.js';
import {renderPaperMarkdown,paperLinkResolver} from './paper-markdown.js';
import {createPaperContextUI} from './paper-context.js';
import {createPaperSourcesUI} from './paper-sources.js';
export function createPapersUI({api,esc,heading,modal,toast,isCurrent,refresh}){
 let active=null;
 const deskUI=createPaperDeskUI({api,esc,modal,toast});
 const flowUI=createPaperFlowUI({esc,modal,toast});
 const sourcesUI=createPaperSourcesUI({api,esc,modal,toast});
 const contextUI=createPaperContextUI({api,esc,modal,toast});
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
   status(c,result.conflict?'Saved versions need comparison. Your draft is kept.':'Saved in Obsidian · '+result.title,result.conflict);
   if(result.conflict)c.blocked=true;
   if(active===c&&$('#paper-writing-state'))$('#paper-writing-state').textContent=Object.hasOwn(c.dirty,'Manuscript prose')?'Draft · unsaved changes':result.writing_status==='complete'?'✓ Approved for export':'Draft saved';
  }catch(error){c.blocked=true;status(c,error.message+' Your editor draft is kept; use Compare & recover.',true)}
  finally{c.saving=false;c.finishSave();if(!c.blocked&&Object.keys(c.dirty).length)c.timer=setTimeout(()=>save(c),200)}
 }
 async function leave(){const c=active;if(c){c.notesResize?.disconnect();clearTimeout(c.timer);await save(c);while(!c.blocked&&Object.keys(c.dirty).length)await save(c)}if(active===c){c?.desk?.dispose();active=null;document.body.classList.remove('paper-desk-mode','desk-show-timer')}}
 function changed(c,name,value){
  c.dirty[name]=value;
  if(name==='Manuscript prose'&&$('#paper-writing-state'))$('#paper-writing-state').textContent='Draft · unsaved changes';
  const kept=putCache(c.cache,{base_hash:c.note.hash,fields:c.dirty});
  status(c,c.blocked?'A version needs comparison. Your editor text is kept.':kept?'Draft kept in this browser · saving shortly…':'Browser recovery is unavailable. Keep this page open until the vault save succeeds.',!kept);
  clearTimeout(c.timer);c.timer=setTimeout(()=>save(c),700);
 }
 function field(name,value,{large=false,placeholder=''}={}){const notes=name==='Notes and bullet points';return `<label class="field paper-field">${esc(name)}<textarea data-paper-field="${esc(name)}" rows="${large?12:notes?8:3}" class="${large?'editor':notes?'paper-notes-editor':''}" placeholder="${esc(placeholder)}">${esc(value||'')}</textarea></label>`}
 function fitNotes(el){
  if(!el.classList.contains('paper-notes-editor')||!el.clientWidth)return;
  const style=getComputedStyle(el),border=parseFloat(style.borderTopWidth)+parseFloat(style.borderBottomWidth);
  el.style.height='auto';el.style.height=Math.ceil(el.scrollHeight+border)+'px';
 }
 function tree(nodes,paper,parent=null,current=null){
  const children=nodes.filter(n=>n.parent_id===parent);if(!children.length)return '';
  return `<ul class="paper-outline-tree">${children.map(n=>`<li><a href="${route(paper,n.id)}" ${n.id===current?'aria-current="page"':''}><small>${esc(n.type)}</small><span>${esc(n.title)}</span>${n.type==='argument'&&n.fields['Manuscript prose']?.trim()?`<span class="paper-has-text" aria-label="${n.writing_status==='complete'?'Complete':'Draft saved'}">${n.writing_status==='complete'?'✓':'●'}</span>`:''}</a>${tree(nodes,paper,n.id,current)}</li>`).join('')}</ul>`;
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
 async function obsidianStarter(){
  const state=await api('/workspace');
  modal('Start a paper in Obsidian',`<p>Create a folder from these Markdown templates, fill it in, then open the paper here. No AI or Overleaf connection is needed.</p><label class="field">Paper title<input id="starter-title" placeholder="For example: Actionability"></label><label class="field">Short paper key<input id="starter-key" placeholder="actionability" pattern="[a-z0-9][a-z0-9_-]*"></label><p class="tiny">Use a different key for each paper. The starter fills matching identifiers into all its files.</p><button class="btn" id="starter-download">Download starter folder</button><p id="starter-status" role="status"></p><ol><li>Unzip the folder into <code>${esc(state.vault+'/'+state.folder)}</code>.</li><li>Open <strong>START_HERE.md</strong>. Fill the purpose in <strong>root.md</strong>, then the section and argument cards in <strong>Cards</strong>.</li><li>The links in <strong>root.md</strong> set the order. Keep the file properties and card headings; write your content underneath.</li><li>Return to Papers and choose <strong>Refresh papers</strong>. Open your new paper and continue writing.</li></ol><p>Writing and reference notes stay in those same Markdown files. The guide explains how to add further sections, arguments and source passages.</p><button class="btn quiet" id="starter-copy-path">Copy the Papers folder path</button>`);
  let customKey=false;$('#starter-key').oninput=()=>customKey=true;
  $('#starter-title').oninput=e=>{if(!customKey)$('#starter-key').value=e.target.value.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')};
  $('#starter-copy-path').onclick=async()=>{try{await navigator.clipboard.writeText(state.vault+'/'+state.folder);toast('Papers folder path copied.')}catch{$('#starter-status').textContent='Copy the Papers folder path shown above.'}};
  $('#starter-download').onclick=async()=>{const button=$('#starter-download');button.disabled=true;try{
   const title=$('#starter-title').value.trim(),key=$('#starter-key').value.trim();if(!title||!/^[a-z0-9][a-z0-9_-]{0,60}$/.test(key))throw new Error('Enter a title and a short key using lowercase letters, numbers, hyphens or underscores.');
   const response=await fetch('/api/workspace/paper-template?'+new URLSearchParams({title,key}));if(!response.ok){const error=await response.json();throw new Error(error.detail||'The starter folder could not be prepared.')}
   const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download=key+'-paper-starter.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);$('#starter-status').textContent='Starter folder downloaded. Unzip it into the Papers folder, then read START_HERE.md.';
  }catch(e){$('#starter-status').textContent=e.message}finally{if(button.isConnected)button.disabled=false}};
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
  const reviews=c.note.type==='argument'?await api(`/workspace/papers/${c.paper}/cards/${c.note.id}/review-drafts`):[];
  const mine={...c.note.fields,...c.dirty};
  const show=fields=>Object.entries(fields).filter(([k,v])=>v&&!['Completed prose hash','Selected review attempt','Completion note'].includes(k)).map(([k,v])=>`<h4>${esc(k)}</h4><p class="prose">${esc(v)}</p>`).join('');
  modal('Compare saved versions',`<div class="paper-compare"><section><h3>Current vault text</h3>${show(latest.fields)}</section><section><h3>My editor draft</h3>${show(mine)}</section></div>${reviews.length?`<details open><summary>Saved review drafts (${reviews.length})</summary>${reviews.map(r=>`<section><h4>${esc(new Date(r.created).toLocaleString())}</h4><p class="prose">${esc(r.text)}</p><button class="btn secondary" data-restore-review="${esc(r.id)}">Restore this manuscript draft</button></section>`).join('')}</details>`:''}<details><summary>Saved vault history (${history.length})</summary>${history.map(r=>`<details><summary>${esc(new Date(r.created).toLocaleString())} · ${esc(r.origin)}</summary>${show(r.fields)}</details>`).join('')}</details><p>Choose deliberately after reading both versions. History is retained.</p><div class="actions"><button class="btn secondary" id="recover-vault">Use current vault text</button><button class="btn" id="recover-mine">Save my displayed draft after comparing</button></div><p id="recovery-status" role="status"></p>`);
  document.querySelectorAll('[data-restore-review]').forEach(b=>b.onclick=async()=>{try{const result=await api(`/workspace/papers/${c.paper}/cards/${c.note.id}/apply-attempt`,{attempt_id:b.dataset.restoreReview,base_hash:latest.hash});if(result.conflict)throw new Error('Compare the competing vault versions first.');putCache(c.cache,null);c.dirty={};c.blocked=false;$('#modal').close();render(c.paper,undefined,c.note.id)}catch(e){$('#recovery-status').textContent=e.message}});
  $('#recover-vault').onclick=async()=>{try{if(latest.conflict)await api(`/workspace/papers/${c.paper}/notes/${c.note.id}`,{base_hash:latest.hash,fields:{},merge_heads:latest.heads.map(h=>h.id)},'PATCH');putCache(c.cache,null);c.dirty={};c.blocked=false;$('#modal').close();render(c.paper,undefined,c.note.id===c.paper?null:c.note.id)}catch(e){$('#recovery-status').textContent=e.message}};
  $('#recover-mine').onclick=async()=>{try{const fields=Object.fromEntries(Object.keys(c.dirty).map(k=>[k,mine[k]]));if(!Object.keys(fields).length)Object.assign(fields,Object.fromEntries(Object.entries(mine).filter(([k])=>c.allowed.includes(k))));await api(`/workspace/papers/${c.paper}/notes/${c.note.id}`,{base_hash:latest.hash,fields,...(latest.conflict?{merge_heads:latest.heads.map(h=>h.id)}:{})},'PATCH');putCache(c.cache,null);c.dirty={};$('#modal').close();render(c.paper,undefined,c.note.id===c.paper?null:c.note.id)}catch(e){$('#recovery-status').textContent=e.message}};
 }
 function mountEditor(c){
  for(const name of ['Notes and bullet points','Reasoning and decisions']){
   const editor=[...document.querySelectorAll('[data-paper-field]')].find(el=>el.dataset.paperField===name);if(!editor)continue;
   const preview=document.createElement('details');preview.className='paper-notes-preview';
   const summary=document.createElement('summary');summary.textContent='Read formatted '+(name==='Notes and bullet points'?'notes':'reasoning');
   const body=document.createElement('div');body.className='paper-markdown';preview.append(summary,body);editor.closest('label').after(preview);
   const update=()=>{body.innerHTML=renderPaperMarkdown(editor.value,{resolve:paperLinkResolver(c.note,c.plan)});};update();editor.addEventListener('input',update);
  }
  const cached=getCache(c.cache);
  if(cached?.fields){c.dirty=cached.fields;c.blocked=cached.base_hash!==c.note.hash;for(const el of document.querySelectorAll('[data-paper-field]'))if(el.dataset.paperField in cached.fields)el.value=cached.fields[el.dataset.paperField];status(c,c.blocked?'Recovered editor text differs from the vault. Compare before saving.':'Recovered your unfinished editor draft.',c.blocked);if(!c.blocked)c.timer=setTimeout(()=>save(c),700)}
  if(c.note.conflict){c.blocked=true;status(c,'Competing saved versions need comparison. You can keep editing your local draft.',true)}
  document.querySelectorAll('[data-paper-field]').forEach(el=>el.addEventListener('input',()=>{fitNotes(el);changed(c,el.dataset.paperField,el.value)}));
  const notes=[...document.querySelectorAll('.paper-notes-editor')],widths=new WeakMap();
  notes.forEach(fitNotes);
  if(window.ResizeObserver){c.notesResize=new ResizeObserver(entries=>{for(const {target} of entries){const width=target.clientWidth;if(width!==widths.get(target)){widths.set(target,width);fitNotes(target)}}});notes.forEach(el=>c.notesResize.observe(el))}
  document.fonts?.ready.then(()=>{if(active===c)notes.forEach(fitNotes)});
  $('#paper-save-now').onclick=()=>{if(c.blocked)compare(c);else save(c)};
  $('#paper-compare').onclick=()=>compare(c);
 }
 async function render(id,serial,cardId){
  if(active)await leave();
  const current=()=>serial===undefined||isCurrent(serial);
  if(!id){
   const data=await api('/workspace');if(!current())return;
   const resume=getCache('awl-paper-resume');
   const vaultName=data.vault?.split(/[\\/]/).filter(Boolean).at(-1)||'Obsidian';
   $('#main').innerHTML=heading('Papers','A home for each paper: its argument plan, notes, sources and manuscript.')+`<div class="papers-home-actions actions"><button class="btn" id="new-paper" ${!data.enabled?'disabled':''}>New paper</button><button class="btn secondary" id="obsidian-paper-starter" ${!data.enabled?'disabled':''}>Obsidian starter templates</button><button class="btn quiet" id="papers-refresh">Refresh papers</button><button class="btn secondary" id="open-paper-folder" ${!data.enabled?'disabled':''}>Open Obsidian paper folder</button></div>${data.enabled?`<details class="vault-connection"><summary><span class="vault-dot" aria-hidden="true"></span>Connected to ${esc(vaultName)}<span class="tiny">Vault & sync settings</span></summary><p class="tiny">${esc(data.vault)} · ${esc(data.folder)}</p><p class="tiny">${esc(data.sync)}</p><div class="actions"><button class="btn secondary" id="select-paper-vault">Change vault</button><button class="btn secondary" id="sync-paper-learning">Sync saved learning</button></div></details>`:`<section class="card"><h2>Connect your Obsidian papers</h2><p>Choose the vault you already sync. Existing paper folders appear here, and new papers are saved there automatically.</p><button class="btn" id="select-paper-vault">Choose Obsidian vault</button><button id="sync-paper-learning" hidden disabled>Sync saved learning</button></section>`}${data.issues.map(x=>`<div class="alert error">${esc(x)}</div>`).join('')}<div class="paper-project-grid">${data.papers.map(p=>`<section class="card paper-project-card"><span class="tag">PAPER PROJECT</span><h2><a href="${route(p.id)}">${esc(p.title)}</a></h2><p>Linked outline, arguments and manuscript text.</p><div class="actions"><a class="btn ${resume?.paper===p.id&&resume.card?'secondary':''}" href="${route(p.id)}">Open outline →</a>${resume?.paper===p.id&&resume.card?`<a class="btn" href="${route(p.id,resume.card)}">Resume writing</a>`:''}<a class="btn quiet" href="${esc(p.uri)}">Open in Obsidian</a></div></section>`).join('')|| (data.enabled?'<section class="card empty"><h2>Your first paper starts here</h2><p>Create a paper with a title and bullet points, or open an existing Obsidian folder with a linked root outline.</p></section>':'')}</div>`;
   $('#select-paper-vault').onclick=setup;$('#new-paper').onclick=newPaper;$('#obsidian-paper-starter').onclick=obsidianStarter;$('#papers-refresh').onclick=()=>render();$('#open-paper-folder').onclick=openFolder;$('#sync-paper-learning').onclick=async()=>{const b=$('#sync-paper-learning');b.disabled=true;b.textContent='Syncing…';try{const r=await api('/workspace/sync',{});toast(r.message+(r.issues?.length?' '+r.issues[0]:''))}catch(e){toast(e.message)}finally{b.disabled=false;b.textContent='Sync saved learning'}};return;
  }
  const plan=await api('/workspace/papers/'+id);if(!current())return;const outside=cardId&&plan.unplaced?.find(n=>n.id===cardId);if(outside){$('#page-label').textContent=outside.title+' · Earlier card';contextUI.outside(plan,outside,getCache('awl-vault-draft-'+id+'-'+cardId));return}const note=cardId?await api(`/workspace/papers/${id}/cards/${cardId}`):plan;if(!current())return;$('#page-label').textContent=cardId?note.title:plan.title+' · Outline';
  putCache('awl-paper-resume',{paper:id,card:cardId});const allowed=cardId?['Purpose','Main message','Scope and boundaries','Notes and bullet points','Writing outline','Source mapping','Manuscript prose','Reasoning and decisions','Next step','Connection to the surrounding argument']:['Research question','Intended contribution','Agreed plan and open questions','Next writing session','Argument order'];
  const c={paper:id,note,allowed,cache:'awl-vault-draft-'+id+'-'+note.id,dirty:{},saving:false,blocked:false};active=c;
  c.plan=plan;
  if(getCache('awl-paper-layout-'+id)!=='planning'){
   document.body.classList.add('paper-desk-mode');
   $('#main').innerHTML=deskUI.shell(plan,note);mountEditor(c);
   const flush=async()=>{await save(c);while(!c.blocked&&Object.keys(c.dirty).length)await save(c);if(c.blocked)throw new Error('Your draft is kept. Compare the saved versions before continuing.');};
   c.desk=deskUI.mount(c,{flush,changed:(name,value)=>changed(c,name,value),isActive:()=>active===c,
    complete:async()=>{const result=await api(`/workspace/papers/${id}/cards/${note.id}/complete`,{base_hash:c.note.hash});if(result.conflict)throw new Error('Compare the saved versions first.');c.note={...c.note,...result};},
    planning:async()=>{try{await flush();putCache('awl-paper-layout-'+id,'planning');await render(id,undefined,cardId)}catch(e){toast(e.message)}}});
   window.dispatchEvent(new CustomEvent('awl-focus-context',{detail:{goal:note.title,route:route(id,cardId),source_path:note.vault_path}}));return;
  }
  const context=n=>n?`<a href="${route(id,n.id)}"><small>${esc(n.type)}</small><strong>${esc(n.title)}</strong><span>${esc(n.fields.Purpose||'Purpose not written yet.')}</span></a>`:'<span class="tiny">Boundary of this part</span>';
  $('#main').innerHTML=`<div class="paper-workspace-header"><div><a href="#papers">← Papers</a><h1>${esc(cardId?note.title:plan.title)}</h1><p>${cardId?`<a href="${route(id)}">${esc(plan.title)} · Whole argument</a>`:'Plan the argument, then develop one card at a time.'}</p></div><div class="actions"><a class="btn secondary" href="${esc(note.uri)}">Open in Obsidian</a><button class="btn secondary" id="add-paper-card">Add card</button><button class="btn secondary" id="paper-import-source">Import source</button><button class="btn secondary" id="paper-find-source">Find source passages</button></div></div>${contextUI.revision(plan)}<div class="paper-workspace-shell"><details class="paper-outline-nav" open><summary>Argument outline</summary>${tree(plan.nodes,id,null,cardId)}${plan.unplaced?.length?`<details><summary>Earlier / unplaced cards (${plan.unplaced.length})</summary><p>These cards are preserved outside the current outline. Read them as reference; the active manuscript uses the outline above.</p>${plan.unplaced.map(n=>`<p><a href="${route(id,n.id)}">${esc(n.title)}</a><code>${esc('[Argument: '+n.title+'](Cards/'+encodeURIComponent(n.filename)+')')}</code></p>`).join('')}</details>`:''}<a href="/api/workspace/papers/${id}/export" class="btn quiet">Download working manuscript</a></details><section class="card paper-writing-panel">${cardId?`<div class="paper-current-position"><span id="paper-writing-state" class="tag ${note.writing_status==='complete'?'green':'neutral'}">${note.writing_status==='complete'?'✓ Complete':note.fields['Manuscript prose']?.trim()?'Draft saved':'Ready to write'}</span><strong>${esc(note.title)}</strong>${note.type==='argument'?`<small>Argument ${flowNeighbours(plan,note.id).index+1} of ${flowNeighbours(plan,note.id).total}</small>`:''}${note.parent?`<a href="${route(id,note.parent.id)}">↑ ${esc(note.parent.title)}</a>`:''}</div>${flowUI.controls(plan,note)}`:`<button type="button" class="btn secondary" id="paper-map">Paper map</button>`}
   ${cardId?contextUI.guidance(note,plan)+field('Purpose',note.fields.Purpose,{placeholder:'What should the reader understand after this argument?'})+ (note.type==='argument'?`<div class="paper-drafting-grid">${field('Notes and bullet points',note.fields['Notes and bullet points'],{placeholder:'Plan, questions and rough ideas…'})}${field('Manuscript prose',note.fields['Manuscript prose'],{large:true,placeholder:'Your actual text. Empty is fine while you plan.'})}</div><details><summary>Original passages and source mapping</summary>${field('Source mapping',note.fields['Source mapping'])}</details>`:field('Main message',note.fields['Main message'])+`<h3>Inside this ${esc(note.type)}</h3>${note.children.length?`<div class="paper-child-cards">${note.children.map(context).join('')}</div>`:'<p>This part can stay empty, or you can add its first card.</p>'}<details><summary>Planning notes and scope</summary>${field('Notes and bullet points',note.fields['Notes and bullet points'])}${field('Scope and boundaries',note.fields['Scope and boundaries'])}${field('Connection to the surrounding argument',note.fields['Connection to the surrounding argument'])}</details>`)+`<details><summary>My reasoning and decisions</summary>${field('Reasoning and decisions',note.fields['Reasoning and decisions'])}</details>${field('Next step',note.fields['Next step'],{placeholder:'One small action to resume…'})}`:
   `${field('Research question',plan.fields['Research question'])}${field('Intended contribution',plan.fields['Intended contribution'])}<h2>The argument at a glance</h2><div class="paper-child-cards">${plan.nodes.filter(n=>!n.parent_id).map(context).join('')}</div><details><summary>Edit the linked outline</summary><p class="tiny">Indent subsections and arguments under their parent. Keep each card link once. Move a whole group together.</p>${field('Argument order',plan.fields['Argument order'],{large:true})}</details><details><summary>Agreed plan and open questions</summary>${field('Agreed plan and open questions',plan.fields['Agreed plan and open questions'])}</details>${field('Next writing session',plan.fields['Next writing session'])}${plan.fields['Preserved material']?'<details class="paper-earlier-material"><summary>Earlier sources & feedback</summary><p class="tiny">These reading notes and earlier drafts remain available as reference. Continue the current manuscript in this paper project.</p><div class="actions"><a class="btn secondary" href="#reader">Saved source-card feedback</a><a class="btn quiet" href="#paper">Earlier writing workspace</a></div></details>':''}`}
   <div class="paper-save-bar"><p id="paper-save-status" role="status">Saved in Obsidian · ${esc(note.title)}</p><button class="btn" id="paper-save-now">Save now</button><button class="btn secondary" id="paper-compare">Compare & recover</button>${note.type==='argument'?'<button class="btn secondary" id="paper-review-argument">Review or ask about my text</button><button class="btn secondary" id="paper-mark-complete">Mark this draft complete</button>':''}</div>${locationHTML(note,esc)}<div id="paper-bottom-navigation"></div><p class="tiny">${esc(plan.sync)} Your private notes remain outside the app’s source code.</p></section></div>`;
  if(['section','subsection'].includes(note.type))$('.paper-workspace-header .actions').insertAdjacentHTML('afterbegin',`<a class="btn" href="#section-writing/${encodeURIComponent(id)}?section=${encodeURIComponent(note.id)}">Write whole section</a>`);
  const writingButton=document.createElement('button');writingButton.className='btn';writingButton.textContent='Return to writing view';writingButton.onclick=async()=>{await save(c);if(c.blocked){toast('Compare the saved versions before switching.');return}putCache('awl-paper-layout-'+id,'writing');await render(id,undefined,cardId)};$('.paper-workspace-header .actions').prepend(writingButton);
  $('#add-paper-card').onclick=()=>addCard(id,plan.nodes,note.type==='argument'?note.parent_id:cardId);
  c.plan=plan;mountEditor(c);
  const flush=async()=>{await save(c);if(c.blocked)throw new Error('Your draft is kept. Compare the saved versions before continuing.');};
  flowUI.bind(plan,note,flush);
  if(note.type==='argument'){
   const neighbours=flowNeighbours(plan,note.id);
   $('#paper-bottom-navigation').innerHTML=neighbours.after?`<button type="button" class="btn" id="paper-next-bottom">Next argument → ${esc(neighbours.after.title)}</button>`:'<p>You have reached the final argument in this outline.</p>';
   if($('#paper-next-bottom'))$('#paper-next-bottom').onclick=()=>$('#paper-next').click();
   $('#paper-mark-complete').onclick=async()=>{try{await flush();const result=await api(`/workspace/papers/${id}/cards/${note.id}/complete`,{base_hash:c.note.hash});if(result.conflict)throw new Error('Compare the saved versions first.');c.note={...c.note,...result};$('#paper-writing-state').textContent='✓ Complete';toast('This manuscript version is complete. Continue with the next argument when ready.');await render(id,undefined,cardId)}catch(e){toast(e.message)}};
  }

  if($('#paper-outline-history'))$('#paper-outline-history').onclick=()=>contextUI.history(plan);
  if($('#paper-review-argument'))$('#paper-review-argument').onclick=async()=>{const b=$('#paper-review-argument');b.disabled=true;try{await save(c);if(c.blocked)throw new Error('Compare your saved versions before reviewing.');const r=await api(`/workspace/papers/${id}/cards/${cardId}/practice`,{});await refresh();location.hash='#practice/'+encodeURIComponent(r.exercise_key)+'?session='+encodeURIComponent(r.session_id)}catch(e){toast(e.message);b.disabled=false}};
  $('#paper-import-source').onclick=()=>sourcesUI.upload(id);
  $('#paper-find-source').onclick=()=>sourcesUI.browse(id,note.type==='argument'?text=>{const el=$('[data-paper-field="Source mapping"]');el.value=el.value.trim()+text;changed(c,'Source mapping',el.value)}:null);
  window.dispatchEvent(new CustomEvent('awl-focus-context',{detail:{goal:note.title,route:route(id,cardId),source_path:note.vault_path}}));
 }
 window.addEventListener('beforeunload',event=>{if(active&&(active.saving||Object.keys(active.dirty).length)){event.preventDefault();event.returnValue=''}});
 return {render,leave};
}
