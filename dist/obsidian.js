export function createObsidianUI({api,esc,heading,toast,isCurrent,refresh}) {
 const $=s=>document.querySelector(s);
 const practice=key=>'#practice/'+encodeURIComponent(key);
 async function render(moduleId,serial){
  const [status,learning]=await Promise.all([api('/obsidian'),api('/courses')]);
  if(!isCurrent(serial))return;
  $('#main').innerHTML=heading('Keep learning between Mac and iPad.','Take a module into Obsidian, write your own answers, and bring them back for review.')+`
   <section class="card companion-flow"><div><span class="tag">1 · PREPARE ON MAC</span><h2>Choose a skill</h2><p>Export a module with its task criteria and examples from other subjects.</p></div><div><span class="tag">2 · WRITE ON IPAD</span><h2>Use Obsidian</h2><p>After Sync finishes, your notes work offline. Write beneath “Your answer”.</p></div><div><span class="tag">3 · REVIEW ON MAC</span><h2>Bring answers back</h2><p>Preview the synced text, save selected answers, then request feedback.</p></div></section>
   <div class="grid companion-grid"><section class="card"><h2>Take a module with you</h2><label class="field">Course and module<select id="companion-module">${learning.courses.map(c=>`<optgroup label="${esc(c.title)}">${c.modules.map(m=>`<option value="${esc(m.id)}">${esc(m.title)} · ${m.total} activities</option>`).join('')}</optgroup>`).join('')}</select></label><p>Existing worksheets keep your answers when you export the same module again.</p><button type="button" class="btn" id="companion-export">Create Obsidian worksheets</button><div id="companion-export-result" role="status"></div></section>
   <section class="card"><h2>See WISE on your iPad</h2><p>Create a Canvas map of the 49 paragraph briefs, with your saved argument notes, and a dated learning progress page.</p><button type="button" class="btn secondary" id="companion-snapshot">Create learning & WISE snapshot</button><div id="companion-snapshot-result" role="status"></div><p class="tiny">Canvas edits and scratch notes stay in Obsidian. Use a WISE module worksheet for paragraphs you want to bring into the lab.</p></section></div>
   <section class="card companion-return"><div class="section-row"><div><h2>Bring back my answers</h2><p>Let Obsidian Sync finish on both devices first. Each import saves a separate version; your existing lab drafts stay available.</p></div><button type="button" class="btn" id="companion-preview">Preview synced answers</button></div><div id="companion-preview-result" aria-live="polite"></div></section>
   <section class="card"><h2>Already in your vault</h2><p class="tiny source-path">${esc(status.vault)} / ${esc(status.folder)}</p><div id="companion-exports">${status.modules.length?status.modules.map(m=>`<p><a href="${esc(m.uri)}">${esc(m.title)}</a> · ${m.count} worksheets</p>`).join(''):'<p>No modules exported yet. Start with “Supply the missing premise”.</p>'}</div><h3>Recent snapshots</h3><div id="companion-snapshots">${status.snapshots.map(s=>`<p><a href="${esc(s.uri)}">${esc(s.title)}</a> · ${esc(new Date(s.created).toLocaleString())}</p>`).join('')||'<p>Create a snapshot to take your WISE map and progress with you.</p>'}</div></section>
   <section class="card"><h2>What works where</h2><div class="table-wrap"><table><thead><tr><th>Where you are</th><th>Available now</th><th>What waits for the Mac</th></tr></thead><tbody><tr><td>At home</td><td>Obsidian worksheets, examples and WISE Canvas</td><td>Import and local tutor review in the Mac lab</td></tr><tr><td>Away, with internet</td><td>The same notes through Obsidian Sync</td><td>Full browser lab access needs a separately configured secure connection</td></tr><tr><td>Offline, Mac off</td><td>Previously synced notes, drafting and visual planning</td><td>Sync, grading, points and tutor feedback</td></tr></tbody></table></div><p>${esc(status.sync_note)}</p><p>For offline work, check that the Companion folder and Canvas files are included in Sync and open them on your iPad before leaving. Resolve any conflict copies before importing. The app never publishes your vault to the internet.</p><p><a href="/api/obsidian/guide" target="_blank">Read the Mac, Obsidian & iPad guide</a></p></section>`;
  $('#companion-module').value=learning.modules.some(m=>m.id===moduleId)?moduleId:'advanced-premises';
  function busy(button,fn){button.disabled=true;return Promise.resolve().then(fn).catch(e=>toast(e.message)).finally(()=>{button.disabled=false})}
  $('#companion-export').onclick=event=>busy(event.currentTarget,async()=>{
   const r=await api('/obsidian/modules',{module_id:$('#companion-module').value});if(!isCurrent(serial))return;
   $('#companion-export-result').innerHTML=`<div class="alert success">${r.already_exported?'Your existing worksheets are ready. Answers were kept.':`${r.count} worksheets created.`} <a href="${esc(r.uri)}">Open this module in Obsidian →</a></div>`;
   if(!r.already_exported)$('#companion-exports').insertAdjacentHTML('beforeend',`<p><a href="${esc(r.uri)}">${esc(r.title)}</a> · ${r.count} worksheets</p>`);
  });
  $('#companion-snapshot').onclick=event=>busy(event.currentTarget,async()=>{
   const r=await api('/obsidian/snapshot',{});if(!isCurrent(serial))return;
   $('#companion-snapshot-result').innerHTML=`<div class="alert success">Snapshot created. <a href="${esc(r.uri)}">Open in Obsidian →</a></div>`;
  });
  $('#companion-preview').onclick=event=>busy(event.currentTarget,async()=>{
   const r=await api('/obsidian/preview');if(!isCurrent(serial))return;
   const ready=r.notes.filter(n=>n.status==='ready'),other=r.notes.filter(n=>n.status==='needs_attention'),imported=r.notes.filter(n=>n.status==='imported').length;
   $('#companion-preview-result').innerHTML=`<p><strong>${ready.length} new answers</strong> · ${imported} already imported · ${r.notes.filter(n=>n.status==='empty').length} still blank.</p>${other.map(n=>`<div class="alert error"><strong>${esc(n.title)}</strong><p>${esc(n.error)}</p><small>${esc(n.path)}</small></div>`).join('')}${ready.length?`<p>Check the exact text below. Choose up to 30 answers to save. This does not mark open writing correct.</p><button type="button" class="btn quiet" id="companion-select-all">Select first ${Math.min(30,ready.length)} answers</button><div class="companion-answer-list">${ready.map(n=>`<article class="companion-answer"><label><input type="checkbox" data-import-note="${esc(n.id)}"> <strong>${esc(n.title)}</strong></label><pre>${esc(n.text)}</pre>${n.outline?`<details><summary>Your idea outline</summary><p class="preserve-lines">${esc(n.outline)}</p></details>`:''}${n.reason?`<p><strong>Your reflection:</strong> ${esc(n.reason)}</p>`:''}</article>`).join('')}</div><button type="button" class="btn" id="companion-import">Save selected answers</button><div id="companion-import-result" role="status"></div>`:'<p>Write in an exported worksheet on the iPad or Mac, then let Sync finish and preview again.</p>'}`;
   if(!ready.length)return;
   $('#companion-select-all').onclick=()=>document.querySelectorAll('[data-import-note]').forEach((el,i)=>el.checked=i<30);
   $('#companion-import').onclick=event=>busy(event.currentTarget,async()=>{
    const selected=[...document.querySelectorAll('[data-import-note]:checked')].map(el=>{const n=ready.find(n=>n.id===el.dataset.importNote);return {note_id:n.id,file_hash:n.file_hash}});
    if(!selected.length||selected.length>30)throw new Error('Select 1–30 answers to save.');
    const result=await api('/obsidian/import',{selected});await refresh();if(!isCurrent(serial))return;
    $('#companion-import-result').innerHTML=`<div class="alert success"><strong>${result.results.length} answers saved.</strong><p>Open an activity for tutor feedback, revision or your own criteria review.</p>${result.results.map(n=>`<p><a href="${practice(n.exercise_key)}">${esc(ready.find(r=>r.id===n.note_id).title)} →</a> · ${n.check.checked?(n.check.correct?'Correct · completion recorded':'Saved · revise the answer'):'Saved · awaiting writing review'}</p>`).join('')}</div>`;
    document.querySelectorAll('[data-import-note]:checked').forEach(el=>{el.checked=false;el.disabled=true});
   });
  });
 }
 return {render};
}
