import {argumentFlowHTML} from './argument-flow.js';
import {wordChanges} from './text-comparison.js';
// Sources remain immutable. Interpretations and manuscript selection are explicit.
export function createRevisionUI({api,esc,heading,toast,modal,getState,isCurrent}) {
 const $=s=>document.querySelector(s);
 let data,doc,selected=null,pendingReuse=null,basket=new Set(),target='I-06',tab='directions',page=0,generation=0,serial;
 let matches=[],matchMeta=null,searchGeneration=0,drawGeneration=0;
 const load=(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch{return d}};
 const keep=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch{}};
 const nodeOptions=()=>data.nodes.map(n=>`<option value="${esc(n.id)}" ${n.id===target?'selected':''}>${esc(n.id+' · '+n.title)}</option>`).join('');
 const scrollTo=e=>{e.style.scrollMarginTop=((document.body.classList.contains('focus-mode')?$('#focus-work')?.offsetHeight:0)||0)+24+'px';e.scrollIntoView({block:'start',behavior:'smooth'})};
 const route=()=>location.hash='#paper/'+encodeURIComponent(target);
 const statusLabel=s=>({proposed:'Proposed · check with the discussion',confirmed:'Confirmed by you',needs_clarification:'Needs clarification',resolved:'Resolved',superseded:'Superseded'}[s]||s);
 const docLink=(d,s)=>'/api/revision/uploads/'+d.id+'/original'+(s?.page?'#page='+s.page:'');
 const practice=(key)=>'#practice/'+encodeURIComponent(key)+'?from='+encodeURIComponent(target);
 const tipHTML=t=>`<details class="revision-tip"><summary>${esc(t.title)}</summary><p><strong>Why here:</strong> ${esc(t.reason)}</p>${t.quote?`<blockquote class="short-quote">${esc(t.quote)}</blockquote>`:''}<p>${esc(t.rule)}</p><p class="tiny">${esc(t.watch)}</p><p><strong>Useful structure:</strong> ${esc(t.pattern)}</p><p><strong>Another field · ${esc(t.example.subject)}:</strong> ${esc(t.example.text)}</p><div class="actions"><a class="btn secondary" href="${practice(t.practice_key)}">Practise, then return to ${esc(target)}</a><a href="${practice(t.warmup_key)}">Start with diagnosis</a><a href="${esc(t.reading.url)}" target="_blank" rel="noreferrer">Read the principle</a></div></details>`;
 async function render(id,s,source={}) {
  serial=s;const token=++generation;
  data=await api('/revision');if(!isCurrent(s)||token!==generation)return;
  target=data.nodes.some(n=>n.id===id)?id:load('awl-writing-resume','I-06');
  if(!data.nodes.some(n=>n.id===target))target='I-06';
  tab=id&&data.nodes.some(n=>n.id===id)?'passages':load('awl-revision-tab','directions');
  if(!['directions','passages','coaching'].includes(tab))tab='directions';
  if(source.reuse&&data.state.reuse_versions[source.reuse]){pendingReuse=data.state.reuse_versions[source.reuse];target=pendingReuse.node_id;source.document=pendingReuse.document_id;source.segment=pendingReuse.segment_ids[0];}
  if(source.document&&data.documents.some(d=>d.id===source.document)){doc=await api('/revision/uploads/'+source.document);if(!isCurrent(s)||token!==generation)return;selected=doc.segments.some(b=>b.id===source.segment)?source.segment:null;basket.clear();tab='passages';}
  $('#main').innerHTML=heading('Keep the argument. Keep the wording that works.','Turn discussion points into decisions, place existing passages, then edit only what the argument needs.',`<a class="btn secondary" href="#paper/${esc(target)}">Return to WISE · ${esc(target)}</a>`)+`
   <div class="revision-path" aria-label="Revision workflow"><span>1 · Check the direction</span><b>→</b><span>2 · Place existing text</span><b>→</b><span>3 · Make one focused edit</span><b>→</b><span>4 · Read in context</span></div>
   <section class="card revision-start"><div class="section-row"><div><h2>Your next small step</h2><p>${Object.values(data.state.decisions).some(d=>d.status==='proposed')?'Review a proposed direction before changing the manuscript. A discussion suggestion becomes confirmed only when you mark it so.':'Choose one argument target. Find an existing passage that already does its job before writing new prose.'}</p></div><label class="field">Current WISE target<select id="revision-target">${nodeOptions()}</select></label></div><div class="actions"><button class="btn secondary" id="revision-write">Open this paragraph desk</button><button class="btn quiet" id="revision-focus">Focus on this target</button></div></section>
   <details class="card" id="revision-upload"><summary>Upload a new discussion, manuscript or card collection</summary><p>Original files and extracted text are saved locally and included in the lab’s full backup. Uploading does not change your argument or manuscript selection.</p><form id="revision-upload-form"><div class="grid"><label class="field">Material type<select name="kind" id="upload-kind"><option value="discussion">Supervisor discussion / remarks</option><option value="manuscript">Current manuscript</option><option value="cards">Argument cards / analysis</option></select></label><label class="field">File<input name="file" type="file" accept=".docx,.pdf,.md,.txt,.zip" required></label><label class="field">PDF layout<select name="columns"><option value="2">Two columns</option><option value="1">One column</option></select></label></div><label class="checkbox-row"><input type="checkbox" name="black_means_agreed" id="upload-black" disabled>In this manuscript, black text means previously agreed wording.</label><p class="tiny">20 MB per file. Selectable PDF text is needed. Colour records your convention; it does not establish scientific validity. Check formulas, tables and text crossing columns against the original.</p><button class="btn" type="submit">Upload and prepare for review</button><p id="upload-status" role="status"></p></form></details>
   <nav class="wb-tabs revision-tabs" aria-label="Revision workspace">${[['directions','Discussion & decisions'],['passages','Existing text & cards'],['coaching','Targeted writing help']].map(([k,t])=>`<button class="btn secondary" data-revision-tab="${k}">${t}</button>`).join('')}</nav><div id="revision-body"></div>
   <footer class="wb-footer"><a href="/api/revision/export">Download revision record</a><button class="btn quiet" id="revision-vault">Back up revision work to Obsidian</button><a href="/api/backup">Full backup including original uploads</a><a href="#guide">Workflow guide</a></footer>`;
  $('#revision-target').onchange=()=>{target=$('#revision-target').value;keep('awl-writing-resume',target);draw()};
  $('#revision-write').onclick=route;
  $('#revision-focus').onclick=()=>window.dispatchEvent(new CustomEvent('awl-focus-request',{detail:{goal:'WISE '+target+': '+data.nodes.find(n=>n.id===target).purpose,route:'#paper/'+target}}));
  document.querySelectorAll('[data-revision-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.revisionTab;keep('awl-revision-tab',tab);draw()});
  $('#upload-kind').onchange=()=>{const b=$('#upload-black');b.disabled=$('#upload-kind').value!=='manuscript';if(b.disabled)b.checked=false};
  $('#revision-upload-form').onsubmit=async e=>{
   e.preventDefault();const form=e.currentTarget,button=form.querySelector('button'),f=form.elements.file.files[0];
   if(!f||f.size>20*1024*1024){$('#upload-status').textContent='Choose a file no larger than 20 MB.';return}
   button.disabled=true;$('#upload-status').textContent='Reading the file and preserving its original…';
   try{
    const body=new FormData(form);body.set('black_means_agreed',form.elements.black_means_agreed.checked?'true':'false');
    const response=await fetch('/api/revision/uploads',{method:'POST',headers:{'X-AWL-Token':getState().token},body});
    const result=await response.json();if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'The upload could not be accepted. Reload and try again.');
    data=await api('/revision');doc=await api('/revision/uploads/'+result.id);basket.clear();selected=null;page=0;tab='passages';
    if(isCurrent(serial)){draw();$('#upload-status').textContent=`${result.filename}: ${result.segments} text blocks prepared. Review the source before recording a decision.`}
   }catch(error){if($('#upload-status'))$('#upload-status').textContent=error.message}finally{button.disabled=false}
  };
  $('#revision-vault').onclick=async()=>{try{const r=await api('/revision/export/vault',{});toast('Revision notes, sources and full lab backup saved to '+r.path)}catch(e){toast(e.message)}};
  draw();
 }
 function draw(){
  if(!isCurrent(serial)||!$('#revision-body'))return;
  document.querySelectorAll('[data-revision-tab]').forEach(b=>{b.classList.toggle('current',b.dataset.revisionTab===tab);b.setAttribute('aria-pressed',String(b.dataset.revisionTab===tab))});
  if(tab==='directions')directions();else if(tab==='passages')passages();else coaching();
 }
 function directions(){
  const records=Object.values(data.state.decisions).sort((a,b)=>b.updated.localeCompare(a.updated));
  const current=records.filter(d=>d.node_ids.includes(target)&&!['resolved','superseded'].includes(d.status));
  $('#revision-body').innerHTML=`<section class="card"><h2>The scientific argument to check</h2><div class="revision-coupling"><div>Research purpose<br><small>What question should the analysis answer?</small></div><b>↔</b><div><strong>One connected argument</strong><br>Problem, response and evidence</div><b>→</b><div>Qualified findings<br><small>What follows, within which limits?</small></div></div><p class="tiny">Working interpretation of the supplied discussion, not a confirmed new manuscript outline. The arrows show design relationships, not a validated feedback loop. The A/B cards are an analysis overlay; the 49 existing writing targets are prompts, not required paragraphs or section headings.</p><div class="actions"><button id="new-decision" class="btn">Record a direction or open question</button><button id="read-discussion" class="btn secondary">Read an uploaded discussion</button></div></section>
   <section class="card"><h2>Directions affecting ${esc(target)} · ${current.length}</h2>${current.length?current.map(decisionHTML).join(''):'<p>No active direction linked yet. Use an exact source passage or record your own planning note.</p>'}</section>
   <details class="card"><summary>All decisions and open questions (${records.length})</summary>${records.map(decisionHTML).join('')}</details>`;
  $('#new-decision').onclick=()=>decisionForm();
  $('#read-discussion').onclick=async()=>{const d=data.documents.filter(d=>d.kind==='discussion').at(-1);doc=d?await api('/revision/uploads/'+d.id):null;selected=null;basket.clear();tab='passages';draw()};
  document.querySelectorAll('[data-edit-decision]').forEach(b=>b.onclick=()=>decisionForm(data.state.decisions[b.dataset.editDecision]));
  document.querySelectorAll('[data-decision-source]').forEach(b=>b.onclick=async()=>{const d=data.state.decisions[b.dataset.decisionSource];doc=await api('/revision/uploads/'+d.document_id);selected=d.segment_id;basket.clear();tab='passages';draw()});
 }
 function decisionHTML(d){return `<article class="revision-decision"><span class="tag ${d.status==='confirmed'?'success':''}">${esc(statusLabel(d.status))}</span><p>${esc(d.text)}</p><small>Targets: ${esc(d.node_ids.join(', '))}</small>${d.quote?`<details><summary>Exact discussion / source excerpt</summary><blockquote>${esc(d.quote)}</blockquote><button class="btn quiet" data-decision-source="${d.id}">Read in source context</button></details>`:'<p class="tiny">Author planning note</p>'}<button class="btn quiet" data-edit-decision="${d.id}">Review or update status</button></article>`}
 function decisionForm(existing=null,source=null){
  const base=data.state.version;const record=existing||{text:'',status:'proposed',node_ids:[target],quote:'',...(source?{document_id:doc.id,segment_id:source.id}: {})};
  const draftKey='awl-decision-draft-'+(existing?.id||source?.id||'new');
  const saved=load(draftKey,null);
  modal(existing?'Review this direction':'Record a direction from the discussion',`
   <p>Separate what was said from your interpretation. Confirm only a direction you consider agreed. A question or provisional suggestion can remain open.</p>
   ${source?`<details open><summary>Selected source · ${esc(source.locator)}</summary><pre class="source-text">${esc(source.text)}</pre></details>`:''}
   <label class="field">Direction or question<textarea id="decision-text" maxlength="4000" rows="4">${esc(saved?.text??record.text)}</textarea></label>
   <label class="field">Status<select id="decision-status">${['proposed','confirmed','needs_clarification','resolved','superseded'].map(s=>`<option value="${s}" ${s===record.status?'selected':''}>${esc(statusLabel(s))}</option>`).join('')}</select></label>
   <fieldset><legend>Affected argument targets</legend><div class="revision-target-picker">${data.nodes.map(n=>`<label class="checkbox-row"><input type="checkbox" data-decision-node="${n.id}" ${record.node_ids.includes(n.id)?'checked':''}>${esc(n.id+' · '+n.title)}</label>`).join('')}</div></fieldset>
   ${record.document_id?`<label class="field">Exact quotation from the selected source<textarea id="decision-quote" rows="3" maxlength="4000">${esc(saved?.quote??record.quote)}</textarea></label><p class="tiny">Copy only the relevant wording. The app checks that the quote occurs in the source block. Speaker labels in automatic transcripts may need correction.</p>`:'<p class="tiny">This will be saved as your own planning note. To attach a quotation, open a source block and choose “Create a direction from this passage”.</p>'}
   <button id="save-decision" class="btn">Save direction</button><p id="decision-error" role="status"></p>`);
  const draft=()=>keep(draftKey,{text:$('#decision-text').value,quote:$('#decision-quote')?.value||''});
  $('#decision-text').oninput=draft;if($('#decision-quote'))$('#decision-quote').oninput=draft;
  $('#save-decision').onclick=async()=>{const b=$('#save-decision');b.disabled=true;try{
   const body={base_version:base,text:$('#decision-text').value,status:$('#decision-status').value,node_ids:[...document.querySelectorAll('[data-decision-node]:checked')].map(x=>x.dataset.decisionNode),document_id:record.document_id||null,segment_id:record.segment_id||null,quote:$('#decision-quote')?.value||''};
   data.state=await api('/revision/decisions'+(existing?'/'+existing.id:''),body,existing?'PUT':'POST');keep(draftKey,null);$('#modal').close();draw();toast('Direction saved. Manuscript wording has not been changed.');
  }catch(e){$('#decision-error').textContent=e.message}finally{b.disabled=false}};
 }
 async function passages(){
  const view=++drawGeneration,where=target;searchGeneration++;
  const valid=()=>isCurrent(serial)&&tab==='passages'&&view===drawGeneration&&where===target;
  if(!doc&&data.documents.length){
   const id=load('awl-revision-document',null);const d=data.documents.find(d=>d.id===id)||data.documents.find(d=>d.kind==='manuscript')||data.documents[0];
   const loaded=await api('/revision/uploads/'+d.id);if(!valid())return;doc=loaded;
  }
  const context=await api('/revision/argument/'+target);if(!valid())return;
  const saved=load('awl-finder-'+doc?.id+'-'+target,{});
  $('#revision-body').innerHTML=argumentFlowHTML(context,esc,{revision:true})+`
   <div class="argument-next"><p>Once the job is clear, look for wording that already serves it.</p><button class="btn" id="argument-find">Find text for this argument →</button><a class="btn quiet" href="#paper/${esc(target)}?write=new">Write a new draft instead</a></div>
   <details class="card passage-workspace" id="finder-work" ${selected||pendingReuse?'open':''}><summary>2 · Find existing passages and decide how to use them</summary><div class="section-row"><h2>Passages for ${esc(target)}</h2><label class="field">Uploaded material<select id="material-select"><option value="">Choose a material</option>${data.documents.map(d=>`<option value="${d.id}" ${doc?.id===d.id?'selected':''}>${esc(d.filename)} · ${d.segments} blocks</option>`).join('')}</select></label></div>${doc?`<p class="tiny">Every text colour is indexed. Black indicates previous agreement only when you declared that convention for this upload.</p><form id="finder-form" class="passage-search-form"><label class="field">Describe the idea, or search for words<input id="passage-search" type="search" maxlength="500" value="${esc(saved.q||'')}" placeholder="Leave empty to use this paragraph’s argument job"></label><button class="btn secondary">Find passages</button></form><div class="revision-filters"><label class="field">Text to include<select id="passage-colour"><option value="all">All colours</option><option value="agreed">Previously agreed black text</option><option value="needs_review">Text whose agreement needs review</option></select></label><label class="field">Show<select id="passage-mode"><option value="matches">Best matches for this argument</option><option value="browse">Browse in source order</option></select></label></div><details><summary>Search options and source limitations</summary><label class="checkbox-row"><input id="passage-structure" type="checkbox">Include headings, tables, references and other blocks</label><p class="tiny">${esc(doc.notice)}</p></details><div class="passage-model-bar"><button class="btn secondary" id="passage-model">Ask local LLM which passages fit</button><small>Optional: reads up to 8 retrieved excerpts and your argument context. The index works immediately.</small></div><div id="passage-model-result" aria-live="polite"></div><p id="passage-search-status" class="tiny" role="status"></p><div class="passage-basket" id="passage-basket"></div><div class="revision-material-grid"><div><div id="passage-list"></div><div class="actions"><button id="passage-prev" class="btn quiet">Previous matches</button><span id="passage-count" class="tiny"></span><button id="passage-next" class="btn quiet">More matches</button></div></div><div id="passage-detail" class="revision-detail"><p class="empty">Open a match to read the original and its neighbouring blocks. Then keep the wording, edit a copy, combine selected blocks, or return to write new prose.</p></div></div>`:'<p>Upload a manuscript, discussion or card collection above to start.</p>'}</details>`;
  $('#argument-find').onclick=()=>{$('#finder-work').open=true;scrollTo($('#finder-work'))};
  $('#material-select').onchange=async e=>{const id=e.target.value;if(!id)return;const loaded=await api('/revision/uploads/'+id);if(!valid()||$('#material-select')?.value!==id)return;doc=loaded;keep('awl-revision-document',doc.id);basket.clear();selected=null;page=0;draw()};
  if(!doc)return;
  $('#passage-colour').value=['all','agreed','needs_review'].includes(saved.colour)?saved.colour:'all';
  $('#passage-mode').value=saved.mode==='browse'?'browse':'matches';$('#passage-structure').checked=!!saved.include_structure;
  $('#finder-form').onsubmit=e=>{e.preventDefault();page=0;refreshMatches()};
  for(const id of ['passage-colour','passage-mode','passage-structure'])$('#'+id).onchange=()=>{page=0;refreshMatches()};
  $('#passage-search').oninput=()=>{searchGeneration++;$('#passage-model-result').replaceChildren();$('#passage-model').disabled=true;$('#passage-search-status').textContent='Press Enter or Find passages to update the matches.'};
  $('#passage-prev').onclick=()=>{page--;drawPassages()};$('#passage-next').onclick=()=>{page++;drawPassages()};
  $('#passage-model').onclick=()=>startPassageReading();
  await refreshMatches();if(!valid())return;
  if(pendingReuse){const version=pendingReuse;pendingReuse=null;basket=new Set(version.segment_ids);reuseForm(doc.segments.find(s=>s.id===version.segment_ids[0]),version);}
  if(selected&&doc.segments.some(s=>s.id===selected))showPassage(selected);
 }
 function finderValues(){return {q:$('#passage-search').value.trim(),colour:$('#passage-colour').value,include_structure:$('#passage-structure').checked,mode:$('#passage-mode').value}}
 async function refreshMatches(){
  const token=++searchGeneration,documentId=doc.id,nodeId=target,values=finderValues();
  const active=()=>isCurrent(serial)&&tab==='passages'&&token===searchGeneration&&doc?.id===documentId&&target===nodeId&&$('#passage-list');
  keep('awl-finder-'+documentId+'-'+nodeId,values);$('#passage-search-status').textContent='Finding matches across the uploaded text…';$('#passage-model-result').replaceChildren();$('#passage-model').disabled=true;
  try{
   const params=new URLSearchParams({node_id:nodeId,q:values.q,colour:values.colour,include_structure:String(values.include_structure)});
   const found=await api('/revision/search/'+documentId+'?'+params);if(!active())return;matchMeta=found;
   matches=values.mode==='browse'&&!values.q?doc.segments.filter(s=>(values.colour==='all'||(values.colour==='agreed')===(s.approval==='agreed_black'))&&(values.include_structure||!(found.structural_ids||[]).includes(s.id))).map(s=>({...s,snippet:s.text.slice(0,350),reasons:[]})):found.results;
   if(values.mode==='browse')matches.sort((a,b)=>doc.segments.findIndex(s=>s.id===a.id)-doc.segments.findIndex(s=>s.id===b.id));
   $('#passage-search-status').textContent=`${found.indexed} source blocks indexed across all colours. ${found.method}`;
   $('#passage-model').disabled=!found.results.length;drawPassages();
   const cached=load('awl-passage-reading-'+found.search_fingerprint,null);if(cached)pollPassageReading(cached,token);
  }catch(e){if(active()){$('#passage-search-status').textContent=e.message;$('#passage-list').replaceChildren()}}
 }
 function drawPassages(){
  if(!$('#passage-list'))return;const size=6;
  page=Math.max(0,Math.min(page,Math.ceil(matches.length/size)-1));
  $('#passage-list').innerHTML=matches.slice(page*size,(page+1)*size).map(s=>`<div class="revision-block ${selected===s.id?'current':''}">${doc.kind==='manuscript'?`<input type="checkbox" data-basket="${s.id}" aria-label="Include ${esc(s.locator)} in selected passage group" ${basket.has(s.id)?'checked':''}>`:''}<button class="btn quiet" data-passage="${s.id}"><small>${esc(s.locator.split('/').at(-1))} · ${esc(s.ink||'colour unknown')} ${s.approval==='agreed_black'?'· previously agreed':''}</small><span>${esc(s.snippet)}</span>${s.reasons?.length?`<small>${esc(s.reasons.join(' · '))}</small>`:''}${Object.values(data.state.placements).some(p=>p.document_id===doc.id&&p.segment_id===s.id)?'<small>✓ Placement recorded</small>':''}</button></div>`).join('')||'<p>No matches in this filter. Try fewer words, all colours, or browse the source. No match does not prove that the idea is absent.</p>';
  $('#passage-count').textContent=`${matches.length} shown${matchMeta?.total>matches.length&&$('#passage-mode').value==='matches'?' of '+matchMeta.total+' matches (top 60)':''} · page ${page+1}/${Math.max(1,Math.ceil(matches.length/size))}`;
  $('#passage-prev').disabled=page===0;$('#passage-next').disabled=(page+1)*size>=matches.length;
  document.querySelectorAll('[data-passage]').forEach(b=>b.onclick=()=>{selected=b.dataset.passage;drawPassages();showPassage(selected)});
  document.querySelectorAll('[data-basket]').forEach(b=>b.onchange=()=>{if(b.checked&&basket.size>=8){b.checked=false;toast('Choose up to eight blocks for one version.');return}if(b.checked)basket.add(b.dataset.basket);else basket.delete(b.dataset.basket);drawPassages();if(selected)showPassage(selected)});
  $('#passage-basket').innerHTML=basket.size?`<strong>${basket.size} source blocks selected for a working copy</strong><p class="tiny">${esc(doc.segments.filter(s=>basket.has(s.id)).map(s=>s.locator).join('; '))}. These stay selected across search filters.</p><div class="actions"><button class="btn" id="combine-passages">${basket.size>1?'Combine these blocks in my working copy':'Use selected block'}</button><button class="btn quiet" id="clear-passages">Clear selection</button></div>`:'';
  if(basket.size){$('#combine-passages').onclick=()=>reuseForm(doc.segments.find(s=>basket.has(s.id)));$('#clear-passages').onclick=()=>{basket.clear();drawPassages();if(selected)showPassage(selected)}}
 }
 async function startPassageReading(){
  const token=searchGeneration,fingerprint=matchMeta?.search_fingerprint,values=finderValues(),id=doc.id,nodeId=target;
  $('#passage-model').disabled=true;$('#passage-model-result').textContent='Queuing the local reading. You can inspect the indexed matches while you wait.';
  try{const job=await api('/revision/passage-readings',{document_id:id,node_id:nodeId,q:values.q,colour:values.colour,include_structure:values.include_structure});keep('awl-passage-reading-'+fingerprint,job.id);if(token===searchGeneration&&$('#passage-model-result'))pollPassageReading(job.id,token)}catch(e){if(token===searchGeneration&&$('#passage-model-result')){$('#passage-model-result').textContent=e.message;$('#passage-model').disabled=false}}
 }
 async function pollPassageReading(id,token){
  const active=()=>isCurrent(serial)&&tab==='passages'&&token===searchGeneration&&$('#passage-model-result');if(!active())return;
  try{const job=await api('/revision/passage-readings/'+id);if(!active())return;
   if(job.status==='queued'||job.status==='running'){$('#passage-model').disabled=true;$('#passage-model-result').innerHTML=`<p role="status">${job.status==='queued'?'Waiting for the local tutor':'Local model is comparing the passages'}… You can use the index below or leave this page. Return to ${esc(target)} to find this reading here.</p>`;setTimeout(()=>pollPassageReading(id,token),2500);return;}
   $('#passage-model').disabled=false;
   if(job.status!=='complete'){$('#passage-model-result').textContent=job.error;return;}
   const r=job.result;$('#passage-model-result').innerHTML=`<details class="passage-reading" open><summary>Local LLM reading · ${job.pool.length} candidate excerpts</summary><p class="tiny">Suggestions from ${esc(job.provenance?.model||'your local model')}, not agreement or a full-paper review. Check every passage in context.</p><p><strong>What may still be missing:</strong> ${esc(r.overall_gap)}</p>${r.candidates.map(x=>`<article><button class="btn quiet" data-model-passage="${esc(x.segment_id)}">${esc(doc.segments.find(s=>s.id===x.segment_id)?.locator||x.segment_id)} · ${esc(x.fit.replaceAll('_',' '))}</button><p class="tiny">Source excerpt · attached from the manuscript${x.source_section&&x.source_section!==matchMeta.context.current.section?' · Source section '+esc(x.source_section)+' → target '+esc(matchMeta.context.current.section)+'. Check whether its role needs to change.':''}</p><blockquote>${esc(x.quote)}${x.quote_truncated?'…':''}</blockquote><p>${esc(x.reason)}</p>${x.still_needed?`<p><strong>Check or add:</strong> ${esc(x.still_needed)}</p>`:''}</article>`).join('')}</details>`;
   document.querySelectorAll('[data-model-passage]').forEach(b=>b.onclick=()=>{selected=b.dataset.modelPassage;drawPassages();showPassage(selected);scrollTo($('#passage-detail'))});
  }catch(e){if(active()){$('#passage-model-result').textContent=e.message;$('#passage-model').disabled=false}}
 }
 async function showPassage(id){
  selected=id;const s=doc.segments.find(x=>x.id===id);if(!s)return;
  const docId=doc.id,index=doc.segments.findIndex(x=>x.id===id);
  const prose=doc.segments.filter(x=>!matchMeta?.structural_ids?.includes(x.id)&&!['reference','figure_or_table','front_matter','heading_or_fragment','archive'].includes(x.role)),proseIndex=prose.findIndex(x=>x.id===id);
  const continuationCandidate=prose[proseIndex+1];
  const continuation=doc.kind==='manuscript'&&s.page&&proseIndex>=0&&continuationCandidate?.page<=s.page+1&&/^[a-z]/.test(continuationCandidate.text.trimStart())&&!/[.!?][’'"\])]*$/.test(s.text.trim())?continuationCandidate:null;
  const continuationHTML=continuation?`<div class="passage-continuation"><strong>This excerpt may continue after a table or page break.</strong><p class="tiny">Next prose block: ${esc(continuation.locator)}. Check the PDF before joining them.</p><pre class="revision-source">${esc(continuation.text)}</pre><button class="btn secondary" id="include-continuation">Select this block and the possible continuation</button></div>`:'';
  const neighbours=[doc.segments[index-1],doc.segments[index+1]].map((x,i)=>x?`<div><button class="btn quiet" data-neighbour="${esc(x.id)}">${i===0?'Previous':'Next'} source block · ${esc(x.locator)}</button><p class="tiny">${esc(x.ink||'colour unknown')} · ${esc(x.role)}</p><pre class="revision-source">${esc(x.text)}</pre></div>`:'').join('');
  $('#passage-detail').innerHTML=`<div class="section-row"><span class="tag">${esc(s.approval==='agreed_black'?'Black · previously agreed':s.ink==='mixed'?'Mixed colours · inspect original':'Agreement needs review')}</span><a href="${docLink(doc,s)}" target="_blank" rel="noreferrer">Open original${s.page?' · p. '+s.page:''}</a></div><p class="tiny">${esc(s.locator)} · ${esc(s.role.replaceAll('_',' '))}</p><p class="text-role source">${doc.kind==='manuscript'?'Original manuscript excerpt · read only':'Uploaded source excerpt · read only'}</p><pre class="revision-source">${esc(s.text)}</pre><details class="passage-neighbours"><summary>Read the blocks before and after this excerpt</summary><p class="tiny">PDF blocks may split a paragraph or include a figure. These are source neighbours, not your planned WISE argument order.</p>${neighbours}</details>${continuationHTML}<p class="text-role working">3 · Decide what to use for ${esc(target)}</p><div class="actions"><button class="btn secondary" id="passage-direction">Create a direction from this passage</button>${doc.kind==='manuscript'?'<button class="btn secondary" id="passage-placement">Record its fit to this target</button><button class="btn" id="passage-reuse">Use this passage · keep or edit a copy</button>':''}</div>${doc.kind==='manuscript'?`<p class="tiny">${basket.size?basket.size+' blocks selected in source order':'This block will be used unless you select a group'}. Selection never awards exercise completion.</p>`:''}<div id="passage-assessment"></div><div id="passage-inspection"><p class="tiny">Finding relevant checks…</p></div>`;
  if($('#include-continuation'))$('#include-continuation').onclick=()=>{if([...new Set([...basket,id,continuation.id])].length>8){toast('Choose up to eight source blocks.');return}basket.add(id);basket.add(continuation.id);drawPassages();showPassage(id)};
  document.querySelectorAll('[data-neighbour]').forEach(b=>b.onclick=()=>{selected=b.dataset.neighbour;drawPassages();showPassage(selected)});
  $('#passage-direction').onclick=()=>decisionForm(null,s);
  if($('#passage-placement'))$('#passage-placement').onclick=()=>placementForm(s);
  if($('#passage-reuse'))$('#passage-reuse').onclick=()=>reuseForm(s);
  const placements=Object.values(data.state.placements).filter(p=>p.document_id===doc.id&&p.segment_id===id);
  $('#passage-assessment').innerHTML=placements.map(p=>`<p><strong>${esc(p.node_id+' · '+p.fit.replaceAll('_',' '))}</strong><br>${esc(p.reason)}</p>`).join('');
  try{
   const analysis=await api('/revision/inspect/'+docId+'/'+id);
   if(!isCurrent(serial)||doc?.id!==docId||selected!==id||!$('#passage-inspection'))return;
   $('#passage-inspection').innerHTML=`${analysis.editorial_suggestions.map(p=>`<div class="wise-directions"><strong>Proposed fit · ${esc(p.node_id)} · ${esc(p.fit.replaceAll('_',' '))}</strong><p>${esc(p.reason)}</p><small>${esc(p.assessed_by)}</small></div>`).join('')}<details><summary>Possible argument targets · inspect before placing</summary><p class="tiny">${esc(analysis.note)}</p>${analysis.candidates.map(c=>`<p><button class="btn quiet" data-candidate="${c.node_id}">${esc(c.node_id+' · '+c.title)}</button><br><small>${esc(c.reason)}</small></p>`).join('')}</details>${analysis.linked_notes.length?`<details><summary>Open linked notes in this uploaded collection (${analysis.linked_notes.length})</summary>${analysis.linked_notes.map(n=>`<button class="btn quiet" data-linked-note="${n.id}">${esc(n.title)}</button>`).join('')}</details>`:''}${analysis.tips.length?'<h3>Revision questions raised by this wording</h3>'+analysis.tips.map(tipHTML).join(''):''}`;
   document.querySelectorAll('[data-candidate]').forEach(b=>b.onclick=()=>{target=b.dataset.candidate;$('#revision-target').value=target;keep('awl-writing-resume',target);draw()});
   document.querySelectorAll('[data-linked-note]').forEach(b=>b.onclick=()=>showPassage(b.dataset.linkedNote));
  }catch(e){if($('#passage-inspection'))$('#passage-inspection').textContent=e.message}
 }
 function placementForm(s){
  const existing=Object.values(data.state.placements).find(p=>p.document_id===doc.id&&p.segment_id===s.id&&p.node_id===target);
  modal('How does this passage fit?',`<p>${esc(s.locator)}</p><label class="field">WISE target<select id="placement-target">${nodeOptions()}</select></label><label class="field">Your assessment<select id="placement-fit">${[['direct','Fits directly'],['slight_changes','Fits with small changes'],['rebuild','Needs a new argument / substantial rewrite'],['reserve','Keep in reserve']].map(([v,t])=>`<option value="${v}" ${existing?.fit===v?'selected':''}>${t}</option>`).join('')}</select></label><label class="field">Why it fits, or what must change<textarea id="placement-reason" rows="3" maxlength="3000">${esc(existing?.reason||'')}</textarea></label><button id="save-placement" class="btn">Save placement assessment</button><p id="placement-error" role="status"></p>`);
  $('#save-placement').onclick=async()=>{try{data.state=await api('/revision/placements',{base_version:data.state.version,document_id:doc.id,segment_id:s.id,node_id:$('#placement-target').value,fit:$('#placement-fit').value,reason:$('#placement-reason').value});$('#modal').close();drawPassages();showPassage(s.id)}catch(e){$('#placement-error').textContent=e.message}};
 }
 async function reuseForm(s,version=null){
  const sourceDoc=doc,reuseTarget=target;const p=await api('/paper');if(!isCurrent(serial)||tab!=='passages'||sourceDoc.id!==doc?.id)return;const ids=basket.size?doc.segments.filter(x=>basket.has(x.id)).map(x=>x.id):[s.id];
  const original=ids.map(id=>doc.segments.find(s=>s.id===id).text).join('\n\n');
  const cache='awl-reuse-draft-'+doc.id+'-'+target+'-'+ids.join('_');
  const recovered=load(cache,{text:version?.text,reason:version?.reason});
  modal('Edit a copy of your manuscript passage',`<p>Target <strong>${esc(target)}</strong>: ${esc(data.nodes.find(n=>n.id===target).purpose)}</p><p>${p.selected[target]?'A manuscript version is already selected here. This will replace its selection; the earlier version remains saved.':'This will select a manuscript version for this target.'}</p><label class="field">What would you like to do?<select id="reuse-mode"><option value="keep">Keep this source wording unchanged</option><option value="adapt">Edit my working copy</option></select></label><div class="revision-compare"><details id="reuse-original" open><summary>Original manuscript · read only</summary><p class="tiny">${esc(sourceDoc.filename)} · ${esc(ids.map(id=>sourceDoc.segments.find(s=>s.id===id).locator).join("; "))}. This extracted source and the uploaded file stay unchanged.</p><pre class="revision-source">${esc(original)}</pre></details><div><label class="field">My working copy<textarea id="reuse-text" rows="9" maxlength="12000" readonly>${esc(original)}</textarea></label></div></div><p id="reuse-edit-state" class="text-role working" role="status"></p><p id="reuse-change-count" class="tiny"></p><details id="reuse-diff"><summary>Compare my changes with the original</summary><div id="reuse-diff-content"></div></details><label class="field">Why this placement works / what I changed<textarea id="reuse-reason" rows="2" maxlength="3000">${esc(recovered.reason||'')}</textarea></label><label class="checkbox-row"><input id="reuse-confirm" type="checkbox">I checked the original, the target’s argument job and this version. Changed wording may need renewed agreement.</label><p class="tiny">PDF line wraps and hyphenation are preserved in “keep” mode. Use adaptation to repair extraction formatting after checking the original. This records manuscript reuse, not an unaided writing exercise.</p><button id="reuse-save" class="btn">Save this copy & select it for WISE</button><p id="reuse-error" role="status"></p>`);
  $('#reuse-original').open=true;
  const mode=$('#reuse-mode'),editor=$('#reuse-text');let adaptation=recovered.text||original;if(version||ids.length>1){mode.value='adapt';editor.readOnly=false;editor.value=adaptation;}
  const changed=()=>{$('#reuse-edit-state').textContent=mode.value==='keep'?'Working copy is locked. Choose “Edit my working copy” above to change words.':'You are editing this working copy. The original manuscript stays unchanged.';if(mode.value==='adapt')adaptation=editor.value;keep(cache,{text:adaptation,reason:$('#reuse-reason').value});$('#reuse-confirm').checked=false;const diff=wordChanges(original,editor.value);$('#reuse-change-count').textContent=editor.value===original?'No changes from the extracted source.':diff.spacingOnly?'Only spacing or line breaks changed; the word sequence is unchanged. Check formatting against the original.':'Words changed: review the comparison and explain the change.';$('#reuse-diff-content').innerHTML='<p class="tiny">'+(diff.coarse?'Long passage: the changed region is shown together.':'Word comparison ignores spacing; the full versions above retain it.')+'</p><p>'+diff.ops.map(x=>x.kind==='removed'?'<del>'+esc(x.text)+'</del>':x.kind==='added'?'<ins>'+esc(x.text)+'</ins>':esc(x.text)).join(' ')+'</p>'};
  mode.onchange=()=>{editor.readOnly=mode.value==='keep';editor.value=mode.value==='keep'?original:adaptation;changed()};editor.oninput=changed;$('#reuse-reason').oninput=()=>keep(cache,{text:adaptation,reason:$('#reuse-reason').value});changed();
  $('#reuse-save').onclick=async()=>{const b=$('#reuse-save');b.disabled=true;try{await api('/revision/reuse/'+reuseTarget,{base_version:p.state.version,document_id:sourceDoc.id,segment_ids:ids,text:editor.value,mode:mode.value,reason:$('#reuse-reason').value,confirmed:$('#reuse-confirm').checked});keep(cache,null);$('#modal').close();toast('Manuscript version selected with its source record.');route()}catch(e){$('#reuse-error').textContent=e.message}finally{b.disabled=false}};
 }
 function coaching(){
  const support=data.support[target];
  $('#revision-body').innerHTML=`<section class="card"><h2>One problem, one useful practice task</h2><p>${esc(support.workflow)}</p><p class="tiny">${esc(support.basis)} · ${support.card_ids.length} source cards considered. These are relevant checks, not an English grade.</p>${support.tips.map(tipHTML).join('')}<p><a class="btn" href="#paper/${esc(target)}">Apply the skill in ${esc(target)}</a></p><details><summary>Earlier retained / adapted versions for this target</summary>${Object.values(data.state.reuse_versions).filter(v=>v.node_id===target).reverse().map(v=>`<p><a href="#revision/${target}?reuse=${v.id}">${esc(v.mode)} · ${esc(new Date(v.created).toLocaleString())}</a><br>${esc(v.reason)}</p>`).join('')||'<p>No retained versions saved yet.</p>'}</details></section><section class="card"><h2>Recent focus intervals</h2>${data.focus_sessions.slice(-5).reverse().map(f=>`<p><strong>${esc(f.goal||'Focus interval')}</strong> · ${f.minutes} minutes · ${esc(f.outcome==='interval_elapsed'?'interval elapsed':'stopped early')}<br><small>${esc(f.next_action?'Next: '+f.next_action:'No handover recorded.')} ${esc(f.parked?'Parked: '+f.parked:'')}</small></p>`).join('')||'<p>No completed focus intervals recorded yet.</p>'}</section><section class="card"><h2>Review another WISE source card</h2><p>Every imported WISE card has a contextual check and up to three linked language lessons. Current checks raise questions about wording; they do not certify the cited evidence.</p><a href="#reader">Browse all 375 source-card reviews</a></section>`;
 }
 return {render};
}
