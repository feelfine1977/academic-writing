// The fiction workspace owns its drafts; it never edits academic writing records.
const clone=value=>JSON.parse(JSON.stringify(value));
export const wordCount=text=>text.trim().split(/\s+/u).filter(Boolean).length;
export function assembleStory(work){return '# '+work.title+'\n\n'+work.scenes.map(s=>'## '+s.title+'\n\n'+(s.text.trim()?s.text:'[Scene not yet written]')).join('\n\n');}
export function sceneFromBeat(field,fields){return {id:crypto.randomUUID(),title:field.label.replace(/^\d+ · /,''),pov:'',era:'',goal:'',obstacle:'',turn:fields[field.id]||'',threads:'',text:'',reviewed:false};}

export function createFictionUI({api,esc,toast,modal,isCurrent}){
 let curriculum=null,ctx=null,timer=null,poll=null;
 const $=s=>document.querySelector(s);
 const base=id=>'/fiction/projects/'+encodeURIComponent(id);
 const route=(id,view='workshop',stage='',scene='')=>'#fiction/'+encodeURIComponent(id)+'?view='+view+(stage?'&step='+stage:'')+(scene?'&scene='+scene:'');
 const storageKey=id=>'wl-fiction-draft-'+id;
 const current=c=>ctx===c&&isCurrent(c.serial);
 function readLocal(id){try{return JSON.parse(localStorage.getItem(storageKey(id))||'null')}catch{return null}}
 function keepLocal(c){try{localStorage.setItem(storageKey(c.p.id),JSON.stringify({base_version:c.p.version,work:c.work}));return true}catch{return false}}
 function clearLocal(id){try{localStorage.removeItem(storageKey(id))}catch{}}
 function status(c,message,error=false){if(current(c)&&$('#fiction-save-status')){const el=$('#fiction-save-status');el.textContent=message;el.classList.toggle('fiction-error',error)}}
 function invalidateFinish(c){if(c.work.lessons.finish)c.work.lessons.finish.checks=[];}
 function changed(c,{material=true}={}){
  if(material)invalidateFinish(c);
  c.dirty=true;c.edit++;const kept=keepLocal(c);
  status(c,kept?'Changes kept in this browser · saving…':'Browser recovery unavailable · saving to the lab…',!kept);
  clearTimeout(timer);timer=setTimeout(()=>save(c),1000);
 }
 async function save(c=ctx){
  if(!c)return true;
  clearTimeout(timer);
  if(c.saving){await c.saving;if(c.error)return false;return c.dirty?save(c):true}
  if(!c.dirty)return !c.error;
  const work=clone(c.work),edit=c.edit;c.error=null;
  c.saving=(async()=>{
   try{
    const p=await api(base(c.p.id),{base_version:c.p.version,work},'PUT');c.p=p;
    if(c.edit===edit){c.work=clone(p.work);c.dirty=false;clearLocal(p.id)}else keepLocal(c);
    status(c,'Saved to Writing Lab · version '+p.version);updateProgress(c);
    return true;
   }catch(error){c.error=error.message;keepLocal(c);status(c,error.message,true);if(current(c))showConflict(c);return false}
   finally{c.saving=null}
  })();
  const ok=await c.saving;
  if(ok&&c.dirty)return save(c);
  return ok;
 }
 function showConflict(c){
  const host=$('#fiction-recovery');if(!host)return;
  host.hidden=false;host.innerHTML=`<strong>Your edits are kept in this browser.</strong><p>${esc(c.error)} You can save a separate story copy without overwriting either draft.</p><div class="actions"><button class="btn secondary" id="fiction-copy-recovery">Save my draft as a new story</button><button class="btn quiet" id="fiction-download-recovery">Download browser draft</button></div>`;
  $('#fiction-copy-recovery').onclick=()=>copyRecovery(c,c.work);
  $('#fiction-download-recovery').onclick=()=>download('story-recovery.json',JSON.stringify(c.work,null,2),'application/json');
 }
 async function copyRecovery(c,work){try{const p=await api('/fiction/projects',{title:(work.title+' (recovered)').slice(0,180),target_words:work.target_words});const copy={...clone(work),title:p.work.title};await api(base(p.id),{base_version:p.version,work:copy},'PUT');c.dirty=false;c.error=null;clearLocal(c.p.id);location.hash=route(p.id)}catch(e){toast(e.message)}}
 function download(name,text,type='text/markdown'){
  const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 function completed(work,s){return work.lessons[s.id]?.checks.length===s.criteria.length}
 function updateProgress(c){
  if(!current(c))return;
  const count=curriculum.stages.filter(s=>completed(c.work,s)).length,words=c.work.scenes.reduce((n,s)=>n+wordCount(s.text),0);
  if($('#fiction-step-count'))$('#fiction-step-count').textContent=count+' / '+curriculum.stages.length+' steps self-reviewed';
  if($('#fiction-progress'))$('#fiction-progress').value=count;
  if($('#fiction-word-total'))$('#fiction-word-total').textContent=words.toLocaleString()+' / '+c.work.target_words.toLocaleString()+' words';
  document.querySelectorAll('[data-step-status]').forEach(el=>{const s=curriculum.stages.find(s=>s.id===el.dataset.stepStatus);el.textContent=completed(c.work,s)?'✓':String(curriculum.stages.indexOf(s)+1).padStart(2,'0')});
 }
 function sourceLinks(ids){return ids.map(id=>curriculum.sources.find(s=>s.id===id)).filter(Boolean).map(s=>`<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)} ↗</a>`).join('');}
 function tutorNames(){return curriculum.tutors.map(t=>`<span>${esc(t.name)}</span>`).join('');}
 async function render(id,serial,params){
  if(!curriculum)curriculum=await api('/fiction/curriculum');if(!isCurrent(serial))return;
  if(!id){await home(serial);return}
  const [p,reviews]=await Promise.all([api(base(id)),api(base(id)+'/reviews')]);if(!isCurrent(serial))return;
  const view=['workshop','scenes','manuscript','bible','readings'].includes(params.get('view'))?params.get('view'):'workshop';
  const stage=curriculum.stages.find(s=>s.id===(params.get('step')||p.work.stage))||curriculum.stages[0];
  ctx={p,work:clone(p.work),serial,view,stage,scene:params.get('scene'),dirty:false,edit:0,reviews,error:null};
  const c=ctx;
  $('#main').innerHTML=`<div class="fiction-studio">
   <div class="fiction-project-top"><a href="#fiction" class="fiction-back">← All stories</a><div class="actions"><button class="btn quiet" id="fiction-history">Saved versions</button><button class="btn secondary" id="fiction-save">Save now</button></div></div>
   <header class="fiction-project-heading"><div><span class="fiction-kicker">YOUR STORY STUDIO</span><h1>${esc(p.work.title)}</h1><p>Time travel · romance · cosy crime · a little mischief</p></div><div class="fiction-progress-block"><span id="fiction-step-count"></span><progress id="fiction-progress" max="${curriculum.stages.length}" value="0" aria-label="Self-reviewed workshop steps"></progress><small id="fiction-word-total"></small></div></header>
   <div class="fiction-tabs" role="navigation" aria-label="Story tools">${[['workshop','Guided workshop'],['scenes','Scene desk'],['manuscript','Manuscript'],['bible','Story bible'],['readings','Reading shelf']].map(([key,label])=>`<a href="${route(id,key,stage.id)}" ${view===key?'class="active" aria-current="page"':''}>${label}</a>`).join('')}</div>
   <p class="fiction-save-status" id="fiction-save-status" role="status">Saved to Writing Lab · version ${p.version}</p>
   <section id="fiction-recovery" class="fiction-recovery" hidden></section><div id="fiction-content"></div></div>`;
  $('#fiction-save').onclick=()=>save(c);$('#fiction-history').onclick=()=>history(c);
  if(view==='workshop')workshop(c);else if(view==='scenes')scenes(c);else if(view==='manuscript')await manuscript(c);else if(view==='bible')bible(c);else readings(c);
  updateProgress(c);showRecovery(c);startPoll(c);
 }
 async function home(serial){
  const projects=await api('/fiction/projects');if(!isCurrent(serial))return;
  $('#main').innerHTML=`<div class="fiction-home">
   <section class="fiction-hero"><div class="fiction-hero-copy"><span class="fiction-kicker">THE FICTION WORKSHOP</span><h1>A little love.<br>A little crime.<br><em>A wrinkle in time.</em></h1><p>Make the story only you could tell. A guided journey from that first “what if?” to a complete manuscript, with a tutor for every twist.</p><a class="btn" href="#fiction-start">Begin your story <span aria-hidden="true">↗</span></a><span class="fiction-hero-meta">14 steps · 8 specialist tutors · your own pace</span></div>
   <div class="fiction-hero-art" aria-hidden="true"><div class="fiction-clock"><span class="fiction-clock-twelve">XII</span><span class="fiction-clock-three">III</span><span class="fiction-clock-six">VI</span><span class="fiction-clock-nine">IX</span><i class="fiction-hand-one"></i><i class="fiction-hand-two"></i><b>✦</b></div><span class="fiction-art-label">EVERY GOOD STORY<br>TAKES ITS OWN TIME</span><span class="fiction-art-note">a clue from yesterday,<br>a kiss for tomorrow.</span></div></section>
   <section class="fiction-path"><div><span>01 / IMAGINE</span><h2>Find the spark</h2><p>Premise, people and a place worth coming home to.</p></div><div><span>02 / CONNECT</span><h2>Weave the threads</h2><p>A fair puzzle, an earned romance and rules time must obey.</p></div><div><span>03 / WRITE</span><h2>Bring it to life</h2><p>Build scenes, find your voice and revise a complete story.</p></div></section>
   <section class="fiction-stories"><div class="fiction-section-heading"><h2>Your stories</h2><p>Planning, drafts and feedback are saved locally.</p></div><div class="fiction-project-grid">${projects.map(p=>`<a class="fiction-project-card" href="${route(p.id,'workshop',p.stage)}"><span class="fiction-kicker">WORK IN PROGRESS</span><h3>${esc(p.title)}</h3><p>${p.completed} of 14 steps self-reviewed · ${p.words.toLocaleString()} words</p><span>Continue writing →</span></a>`).join('')}
   <form id="fiction-create" class="fiction-new-story"><h3>Start a new story</h3><label class="field">Working title<input name="title" value="My time travel mystery" maxlength="180" required></label><label class="field">Word target<input name="words" type="number" min="500" max="200000" value="8000" required></label><small>A flexible goal. Try 5,000–10,000 words for a first complete adventure, or choose a longer project.</small><button class="btn" type="submit">Create my workshop →</button></form></div></section>
   <section class="fiction-tutor-intro"><span class="fiction-kicker">A SMALL FACULTY, ALL FOR YOUR STORY</span><h2>Meet your writing companions.</h2><p>Short lessons and self-review work any time. For tailored feedback, use your selected local AI model. Each tutor takes a different craft perspective; you decide what belongs in your story.</p><div class="fiction-tutor-list">${tutorNames()}</div><p class="fiction-source-foot">Built with craft ideas from Brandon Sanderson’s lectures, your two PDFs, Writing Excuses and Randy Ingermanson. Original exercises and examples; independent tutors, not the named authors.</p></section></div>`;
  $('.fiction-hero a').onclick=e=>{e.preventDefault();$('#fiction-create').scrollIntoView({behavior:'smooth',block:'center'});$('#fiction-create input').focus({preventScroll:true})};
  $('#fiction-create').onsubmit=async e=>{e.preventDefault();const button=e.currentTarget.querySelector('button');button.disabled=true;try{const form=new FormData(e.currentTarget);const p=await api('/fiction/projects',{title:String(form.get('title')),target_words:Number(form.get('words'))});location.hash=route(p.id)}catch(error){toast(error.message);button.disabled=false}};
 }
 function showRecovery(c){
  const recovered=readLocal(c.p.id);if(!recovered||JSON.stringify(recovered.work)===JSON.stringify(c.work))return;
  const host=$('#fiction-recovery');host.hidden=false;
  const same=recovered.base_version===c.p.version;
  host.innerHTML=`<strong>A browser draft is available.</strong><p>${same?'Your last edits were not saved to the lab.':'The saved story and this browser draft have different versions. Keep both by recovering into a new story.'}</p><div class="actions"><button class="btn secondary" id="fiction-recover">${same?'Resume my browser draft':'Save browser draft as a new story'}</button><button class="btn quiet" id="fiction-compare">Compare drafts</button><button class="btn quiet" id="fiction-dismiss">Use saved story</button></div>`;
  $('#fiction-recover').onclick=async()=>{if(!same){await copyRecovery(c,recovered.work);return}c.work=recovered.work;c.dirty=true;c.edit++;if(await save(c))await render(c.p.id,c.serial,new URLSearchParams('view='+c.view+'&step='+c.stage.id))};
  $('#fiction-compare').onclick=()=>modal('Compare recovery copies',`<p>Download the browser version before discarding it if you want to keep both.</p><button class="btn secondary" id="fiction-get-recovery">Download browser draft</button><div class="fiction-compare"><section><h3>Browser draft</h3><pre>${esc(JSON.stringify(recovered.work,null,2))}</pre></section><section><h3>Saved story</h3><pre>${esc(JSON.stringify(c.work,null,2))}</pre></section></div>`)||null;
  $('#fiction-compare').addEventListener('click',()=>{$('#fiction-get-recovery').onclick=()=>download('story-recovery.json',JSON.stringify(recovered.work,null,2),'application/json')});
  $('#fiction-dismiss').onclick=()=>{clearLocal(c.p.id);host.hidden=true};
 }
 function worksheet(c){return c.work.lessons[c.stage.id]||{fields:{},checks:[]}}
 function workshop(c){
  const s=c.stage,idx=curriculum.stages.indexOf(s),work=worksheet(c);
  $('#fiction-content').innerHTML=`<div class="fiction-workshop-grid"><aside class="fiction-roadmap"><h2>Your workshop</h2><p>Follow the path or revisit any step.</p><nav aria-label="Workshop steps">${curriculum.stages.map(step=>`<a href="${route(c.p.id,'workshop',step.id)}" ${s.id===step.id?'class="active" aria-current="step"':''}><span data-step-status="${step.id}"></span><span>${esc(step.title)}</span></a>`).join('')}</nav></aside><div class="fiction-work-area">
   <header class="fiction-lesson-heading"><span class="fiction-kicker">STEP ${String(idx+1).padStart(2,'0')} / ${curriculum.stages.length} · ABOUT ${s.minutes} MIN</span><h2>${esc(s.title)}</h2><p>${esc(s.subtitle)}</p><button class="btn quiet fiction-tutor-jump" id="fiction-tutor-jump">Talk to your tutor ↓</button></header>
   <section class="fiction-lesson"><h3>The craft idea</h3><p>${esc(s.lesson)}</p><div class="fiction-exercise"><span>TRY THIS</span><p>${esc(s.exercise)}</p></div><details class="fiction-sources"><summary>Where this lesson comes from</summary>${sourceLinks(s.sources)}</details></section>
   <section class="fiction-worksheet"><h3>Your working notes</h3><p class="fiction-muted">Rough answers are enough to begin. You can change your mind.</p>${s.fields.map(f=>`<label class="field">${esc(f.label)}<small>${esc(f.prompt)}</small><textarea data-fiction-field="${f.id}" rows="${f.rows}" maxlength="12000" placeholder="Start with a few words…">${esc(work.fields[f.id]||'')}</textarea>${f.example?`<details><summary>See an original example</summary><p>${esc(f.example)}</p><small>An illustration to learn from. It is not added to your story.</small></details>`:''}</label>`).join('')}
   ${s.id==='scenes'?`<a class="btn" href="${route(c.p.id,'scenes',s.id)}">Open your Scene desk →</a>`:''}
   ${['revision','finish'].includes(s.id)?`<a class="btn secondary" href="${route(c.p.id,'manuscript',s.id)}">Read your assembled manuscript →</a>`:''}</section>
   <section class="fiction-checks"><span class="fiction-kicker">PAUSE & REVIEW</span><h3>Is this doing the job you want?</h3><p>These are your checks, not a tutor’s grade. Editing the notes opens the checks again.</p>${s.criteria.map((text,i)=>`<label><input type="checkbox" data-fiction-check="${i}" ${work.checks.includes(i)?'checked':''}><span>${esc(text)}</span></label>`).join('')}<div class="fiction-next"><button class="btn secondary" id="fiction-save-step">Save this step</button>${idx<curriculum.stages.length-1?`<button class="btn" id="fiction-next">Save & continue →</button>`:`<a class="btn" href="${route(c.p.id,'manuscript')}">Finish & export →</a>`}</div></section>
   </div><aside class="fiction-tutor" id="fiction-tutor"></aside></div>`;
  document.querySelectorAll('[data-fiction-field]').forEach(el=>el.oninput=()=>{
   const w=c.work.lessons[s.id]||={fields:{},checks:[]};w.fields[el.dataset.fictionField]=el.value;w.checks=[];
   document.querySelectorAll('[data-fiction-check]').forEach(cb=>cb.checked=false);changed(c,{material:s.id!=='finish'});
  });
  document.querySelectorAll('[data-fiction-check]').forEach(el=>el.onchange=async()=>{
   const on=el.checked,i=Number(el.dataset.fictionCheck);el.disabled=true;
   if(await save(c)){const w=c.work.lessons[s.id]||={fields:{},checks:[]};if(!Object.values(w.fields).some(v=>v.trim())){toast('Add some working notes before reviewing this step.');el.checked=false}else{w.checks=on?[...new Set([...w.checks,i])]:w.checks.filter(n=>n!==i);changed(c,{material:false});await save(c)}}else el.checked=!on;
   el.disabled=false;updateProgress(c);
  });
  $('#fiction-save-step').onclick=()=>save(c);
  if($('#fiction-next'))$('#fiction-next').onclick=async()=>{if(await save(c)){c.work.stage=curriculum.stages[idx+1].id;changed(c,{material:false});if(await save(c))location.hash=route(c.p.id,'workshop',c.work.stage)}};
  mountTutor(c);
  $('#fiction-tutor-jump').onclick=()=>{$('#fiction-tutor').scrollIntoView({behavior:'smooth',block:'start'});$('#fiction-question').focus({preventScroll:true})};
 }
 function mountTutor(c){
  const s=c.stage;
  $('#fiction-tutor').innerHTML=`<div class="fiction-tutor-head"><span class="fiction-avatar" aria-hidden="true">✦</span><div><span class="fiction-kicker">AT YOUR SIDE</span><h3>Your tutor</h3></div></div><label class="field">Choose a perspective<select id="fiction-tutor-select">${curriculum.tutors.map(t=>`<option value="${t.id}" ${s.tutor===t.id?'selected':''}>${esc(t.name)}</option>`).join('')}</select></label><p id="fiction-tutor-focus"></p><label class="field">What would help right now?<textarea id="fiction-question" rows="3" maxlength="1500" placeholder="For example: Does the clue make the solution too obvious?"></textarea></label><button class="btn" id="fiction-review">Save & ask the tutor</button>${c.view==='scenes'?'<button class="btn secondary" id="fiction-draft">Suggest an optional scene draft</button>':''}<p class="fiction-small">Local AI feedback on this ${c.view==='scenes'?'scene':'worksheet'} and short planning excerpts. Advice is a proposal; you choose what to use. <a href="#settings">Tutor settings</a></p><div id="fiction-tutor-results" aria-live="polite"></div>`;
  const focus=()=>{$('#fiction-tutor-focus').textContent=curriculum.tutors.find(t=>t.id===$('#fiction-tutor-select').value).focus};focus();$('#fiction-tutor-select').onchange=focus;
  $('#fiction-review').onclick=()=>ask(c,'review');if($('#fiction-draft'))$('#fiction-draft').onclick=()=>ask(c,'draft');showReviews(c);
 }
 async function ask(c,mode){
  const question=$('#fiction-question').value,tutor=$('#fiction-tutor-select').value;
  if(!await save(c))return;
  $('#fiction-review').disabled=true;if($('#fiction-draft'))$('#fiction-draft').disabled=true;
  try{const j=await api(base(c.p.id)+'/reviews',{base_version:c.p.version,stage:c.stage.id,scene_id:c.view==='scenes'?selectedScene(c)?.id:null,tutor,question,mode});c.reviews.unshift(j);if(current(c)){showReviews(c);startPoll(c)}}catch(error){toast(error.message);if(current(c)){$('#fiction-tutor-results').innerHTML=`<p class="fiction-error" role="alert">${esc(error.message)}</p>`}}
  finally{if(current(c)){const busy=c.reviews.some(j=>['queued','running'].includes(j.status));$('#fiction-review').disabled=busy;if($('#fiction-draft'))$('#fiction-draft').disabled=busy}}
 }
 function relevantReviews(c){return c.reviews.filter(j=>c.view==='scenes'?j.scene_id===selectedScene(c)?.id:!j.scene_id&&j.stage===c.stage.id)}
 function showReviews(c){
  const host=$('#fiction-tutor-results');if(!current(c)||!host)return;
  const jobs=relevantReviews(c),busy=c.reviews.some(j=>['queued','running'].includes(j.status));
  $('#fiction-review').disabled=busy;if($('#fiction-draft'))$('#fiction-draft').disabled=busy;
  host.innerHTML=(busy?'<p class="fiction-busy">Your local tutor is working. Keep writing; the saved review will appear here.</p>':'')+jobs.slice(0,8).map((j,i)=>{
   const r=j.result,name=curriculum.tutors.find(t=>t.id===j.tutor)?.name||j.tutor;
   return `<details class="fiction-feedback" ${i===0?'open':''}><summary>${esc(name)} · saved v${j.project_version} · ${esc(j.status)}</summary><p class="fiction-small">${esc(new Date(j.created).toLocaleString())} · ${j.project_version===c.p.version?'Review of the current saved project.':'Review of an earlier saved version. Compare it with your current writing.'}</p>${j.question?`<p><strong>Your question:</strong> ${esc(j.question)}</p>`:''}${j.error?`<p class="fiction-error">${esc(j.error)}</p>`:''}${r?`<p>${esc(r.summary)}</p><details><summary>What the tutor read</summary><p>${esc(j.scope)}</p><p>${esc(r.scope)}</p></details>${r.strengths.length?'<h4>Keep what works</h4>'+r.strengths.map(x=>`<blockquote>${esc(x.quote)}</blockquote><p>${esc(x.explanation)}</p>`).join(''):''}<h4>Craft checks</h4>${r.criteria.map(x=>`<p><span class="fiction-criterion-status">${esc(x.status)}</span> ${esc((j.scene_id?curriculum.scene_criteria:curriculum.stages.find(s=>s.id===j.stage).criteria)[x.index])}<small>${esc(x.reason)}</small></p>`).join('')}${r.priorities.length?'<h4>Try next</h4>'+r.priorities.map(x=>`${x.quote?`<blockquote>${esc(x.quote)}</blockquote>`:''}<p>${esc(x.reason)} <strong>${esc(x.action)}</strong></p>`).join(''):''}<h4>A small exercise</h4><p>${esc(r.exercise)}</p><h4>A question to explore</h4><p>${esc(r.next_question)}</p>${r.example?`<details><summary>Optional draft proposal</summary><p class="fiction-small">AI-generated suggestion for your review. Appending it keeps existing prose. Edit it in your own voice.</p><div class="fiction-prose-proposal">${esc(r.example)}</div>${c.view==='scenes'?`<button class="btn secondary" data-use-draft="${j.id}">Append this proposal to my scene</button>`:''}</details>`:''}`:''}</details>`
  }).join('');
  document.querySelectorAll('[data-use-draft]').forEach(button=>button.onclick=()=>{
   const job=jobs.find(j=>j.id===button.dataset.useDraft),scene=selectedScene(c);if(!scene)return;
   scene.text+=(scene.text?'\n\n':'')+job.result.example;scene.reviewed=false;changed(c);$('#fiction-scene-text').value=scene.text;$('#fiction-scene-reviewed').checked=false;$('#fiction-scene-words').textContent=wordCount(scene.text)+' words';button.disabled=true;toast('Proposal appended. Review and revise it in the scene editor.');
  });
 }
 function startPoll(c){
  clearTimeout(poll);
  if(!current(c)||!c.reviews.some(j=>['running','queued'].includes(j.status)))return;
  poll=setTimeout(async()=>{try{const jobs=await api(base(c.p.id)+'/reviews');if(current(c)){c.reviews=jobs;showReviews(c);startPoll(c)}}catch{if(current(c)){status(c,'Could not refresh tutor feedback. Your saved writing is safe.',true);poll=setTimeout(()=>startPoll(c),5000)}}},2500);
 }
 function selectedScene(c){return c.work.scenes.find(s=>s.id===c.scene)||c.work.scenes[0]}
 function newScene(){return {id:crypto.randomUUID(),title:'Untitled scene',pov:'',era:'',goal:'',obstacle:'',turn:'',threads:'',text:'',reviewed:false}}
 async function addScene(c){const s=newScene();c.work.scenes.push(s);c.scene=s.id;changed(c);if(await save(c))location.hash=route(c.p.id,'scenes','scenes',s.id)}
 function scenes(c){
  c.stage=curriculum.stages.find(s=>s.id==='scenes');const scene=selectedScene(c);if(scene)c.scene=scene.id;
  $('#fiction-content').innerHTML=`<div class="fiction-section-heading"><div><span class="fiction-kicker">ONE SCENE AT A TIME</span><h2>Your Scene desk</h2><p>Write in the order you like. Arrange the cards in the order your reader will discover them.</p></div><div class="actions"><button class="btn secondary" id="fiction-seed-scenes">Add cards from my seven plot turns</button><button class="btn" id="fiction-add-scene">+ Add scene</button></div></div>
   <div class="fiction-scene-grid"><aside class="fiction-scene-list" aria-label="Scene order">${c.work.scenes.map((s,i)=>`<div class="fiction-scene-card ${scene?.id===s.id?'active':''}"><a href="${route(c.p.id,'scenes','scenes',s.id)}"><span>${String(i+1).padStart(2,'0')} ${s.reviewed?'· ✓':''}</span><strong>${esc(s.title)}</strong><small>${esc(s.era||'Era to decide')} · ${wordCount(s.text)} words</small></a><div><button class="btn quiet" data-move-scene="${s.id}" data-direction="-1" ${i===0?'disabled':''} aria-label="Move ${esc(s.title)} earlier">↑</button><button class="btn quiet" data-move-scene="${s.id}" data-direction="1" ${i===c.work.scenes.length-1?'disabled':''} aria-label="Move ${esc(s.title)} later">↓</button></div></div>`).join('')||'<p>Your story starts with its first scene. Add a blank card, or use the plot turns you wrote in step 10.</p>'}</aside>
   ${scene?`<section class="fiction-scene-editor"><label class="field">Scene title<input id="fiction-scene-title" data-scene-field="title" maxlength="180" value="${esc(scene.title)}"></label><div class="fiction-scene-meta">${[['pov','Viewpoint character',300],['era','Date / era / branch',300]].map(([key,label,max])=>`<label class="field">${label}<input data-scene-field="${key}" maxlength="${max}" value="${esc(scene[key])}"></label>`).join('')}</div><details class="fiction-scene-plan" ${scene.text?'':'open'}><summary>Plan the scene’s job</summary>${[['goal','What does this person want right now?'],['obstacle','What gets in the way?'],['turn','What changes, and what follows?'],['threads','Clue IDs · relationship turn · time rule · comic beat']].map(([key,label])=>`<label class="field">${label}<textarea data-scene-field="${key}" rows="2" maxlength="${key==='threads'?2000:1500}">${esc(scene[key])}</textarea></label>`).join('')}</details><label class="field fiction-draft-field">Your scene<textarea id="fiction-scene-text" data-scene-field="text" maxlength="60000" rows="20" placeholder="Let something happen. You can make it beautiful later.">${esc(scene.text)}</textarea></label><div class="fiction-scene-footer"><span id="fiction-scene-words">${wordCount(scene.text)} words</span><button class="btn secondary" id="fiction-save-scene">Save scene</button></div><label class="fiction-scene-reviewed"><input type="checkbox" id="fiction-scene-reviewed" ${scene.reviewed?'checked':''}> I have read this version and reviewed its place in the story.</label><details class="fiction-remove"><summary>Remove this scene</summary><p>Earlier saved versions remain available in Saved versions.</p><button class="btn danger" id="fiction-remove-scene">Remove this scene from the manuscript</button></details></section><aside class="fiction-tutor" id="fiction-tutor"></aside>`:'<section class="fiction-empty"><span aria-hidden="true">✎</span><h3>Make room for the first scene.</h3><p>A goal. A complication. A small change that starts something bigger.</p></section>'}</div>`;
  $('#fiction-add-scene').onclick=()=>addScene(c);
  $('#fiction-seed-scenes').onclick=async()=>{const plot=c.work.lessons.plot?.fields||{};if(!Object.values(plot).some(v=>v.trim())){toast('Write a few plot turns in step 10 first.');return}const stage=curriculum.stages.find(s=>s.id==='plot');c.work.scenes.push(...stage.fields.map(f=>sceneFromBeat(f,plot)));changed(c);if(await save(c))scenes(c)};
  document.querySelectorAll('[data-move-scene]').forEach(button=>button.onclick=async()=>{const i=c.work.scenes.findIndex(s=>s.id===button.dataset.moveScene),j=i+Number(button.dataset.direction);[c.work.scenes[i],c.work.scenes[j]]=[c.work.scenes[j],c.work.scenes[i]];changed(c);if(await save(c))scenes(c)});
  if(!scene)return;
  document.querySelectorAll('[data-scene-field]').forEach(el=>el.oninput=()=>{const live=selectedScene(c);live[el.dataset.sceneField]=el.value;live.reviewed=false;$('#fiction-scene-reviewed').checked=false;$('#fiction-scene-words').textContent=wordCount(live.text)+' words';changed(c)});
  $('#fiction-save-scene').onclick=()=>save(c);
  $('#fiction-scene-reviewed').onchange=async e=>{const checked=e.target.checked;if(await save(c)){const live=selectedScene(c);if(!live.text.trim()){toast('Write the scene before marking it reviewed.');e.target.checked=false;return}live.reviewed=checked;changed(c);await save(c)}};
  $('#fiction-remove-scene').onclick=async()=>{if(!await save(c))return;c.work.scenes=c.work.scenes.filter(s=>s.id!==c.scene);c.scene=c.work.scenes[0]?.id||'';changed(c);if(await save(c)){location.hash=route(c.p.id,'scenes','scenes',c.scene);scenes(c)}};
  mountTutor(c);
 }
 async function manuscript(c){
  const audit=await api(base(c.p.id)+'/audit');if(!current(c))return;
  $('#fiction-content').innerHTML=`<div class="fiction-manuscript-layout"><aside class="fiction-manuscript-tools"><span class="fiction-kicker">THE WHOLE STORY</span><h2>From first page to last.</h2><p>${audit.words.toLocaleString()} words · ${audit.scenes} ${audit.scenes===1?'scene':'scenes'}</p><label class="field">Story title<input id="fiction-final-title" maxlength="180" value="${esc(c.work.title)}"></label><label class="field">Word target<input id="fiction-target" type="number" min="500" max="200000" value="${c.work.target_words}"></label><button class="btn secondary" id="fiction-update-title">Save title & target</button><hr><button class="btn" id="fiction-export-draft">Download draft · Markdown</button><button class="btn secondary" id="fiction-export-finished" ${audit.ready?'':'disabled'}>Download finished story</button><button class="btn quiet" id="fiction-print">Print / save PDF</button><p class="fiction-small">Exports use your ordered scene prose. Printing includes the manuscript only; choose Save as PDF in your print dialog.</p><div class="fiction-audit"><h3>${audit.ready?'Ready for your finished export':'Before the finished export'}</h3>${audit.gaps.length?'<ul>'+audit.gaps.map(g=>`<li>${esc(g)}</li>`).join('')+'</ul>':'<p>Your scenes and final checks are reviewed.</p>'}<a href="${route(c.p.id,'workshop','finish')}">Open the final checks →</a><p class="fiction-small">${esc(audit.notice)}</p></div></aside><article class="fiction-manuscript" id="fiction-manuscript"><header><span>A STORY BY YOU</span><h1>${esc(c.work.title)}</h1></header>${c.work.scenes.map(s=>`<section><h2>${esc(s.title)}</h2>${s.text.trim()?s.text.split(/\n\s*\n/).map(p=>`<p>${esc(p)}</p>`).join(''):'<p class="fiction-gap">This scene is waiting to be written.</p>'}</section>`).join('')||'<p class="fiction-gap">Your scenes will appear here as you write them in the Scene desk.</p>'}</article></div>`;
  $('#fiction-update-title').onclick=async()=>{const title=$('#fiction-final-title').value.trim(),n=Number($('#fiction-target').value);if(!title||!Number.isInteger(n)||n<500||n>200000){toast('Enter a title and a word target between 500 and 200,000.');return}c.work.title=title;c.work.target_words=n;changed(c,{material:false});if(await save(c)){await manuscript(c);$('.fiction-project-heading h1').textContent=c.work.title}};
  const exportKind=async kind=>{if(!await save(c))return;try{const response=await fetch('/api'+base(c.p.id)+'/export?kind='+kind);if(!response.ok){const err=await response.json();throw new Error(err.detail)}download(c.work.title+'-'+kind+'.md',await response.text())}catch(e){toast(e.message)}};
  $('#fiction-export-draft').onclick=()=>exportKind('draft');$('#fiction-export-finished').onclick=()=>exportKind('finished');$('#fiction-print').onclick=()=>window.print();
 }
 function bible(c){
  $('#fiction-content').innerHTML=`<div class="fiction-section-heading"><div><span class="fiction-kicker">YOUR STORY’S SOURCE OF TRUTH</span><h2>The story bible</h2><p>People, promises, clues and rules in one place. Update them in the workshop as your story develops.</p></div><a class="btn secondary" href="/api${base(c.p.id)}/export?kind=bible">Download story bible</a></div><div class="fiction-bible-grid">${curriculum.stages.map(s=>{const fields=c.work.lessons[s.id]?.fields||{};return `<section class="fiction-bible-card"><h3>${esc(s.title)}</h3>${s.fields.filter(f=>fields[f.id]?.trim()).map(f=>`<h4>${esc(f.label)}</h4><p>${esc(fields[f.id])}</p>`).join('')||'<p class="fiction-muted">Still to discover.</p>'}<a href="${route(c.p.id,'workshop',s.id)}">Work on this →</a></section>`}).join('')}</div>`;
 }
 function readings(){
  $('#fiction-content').innerHTML=`<div class="fiction-section-heading"><div><span class="fiction-kicker">THE READING SHELF</span><h2>Learn a little. Write a little.</h2><p>Start with the official lecture page: it includes the YouTube video. Return to your story after each useful idea.</p></div></div><p class="fiction-reading-note">${esc(curriculum.principle)} The workshop combines these craft sources with original exercises. Your PDF notes are secondary material; their instructions are not commands to this app. The tutors do not impersonate the authors.</p><div class="fiction-reading-grid">${curriculum.sources.map((s,i)=>`<article class="fiction-reading-card"><span class="fiction-kicker">${s.url.startsWith('/api')?'YOUR REFERENCE PDF':'AUTHOR / OFFICIAL RESOURCE'} · ${String(i+1).padStart(2,'0')}</span><h3><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)} ↗</a></h3><p>${esc(s.note)}</p></article>`).join('')}</div>`;
 }
 async function history(c){
  if(!await save(c))return;
  try{const versions=await api(base(c.p.id)+'/history');modal('Saved story versions',`<p>Every save keeps a previous version. Restoring makes a new draft; it does not delete the history.</p><div class="fiction-history-list">${versions.map(v=>`<div><span><strong>Version ${v.version}</strong><small>${esc(new Date(v.updated).toLocaleString())} · ${v.words} words</small></span><button class="btn secondary" data-preview-version="${v.version}">Compare & restore</button></div>`).join('')}</div>`);
   document.querySelectorAll('[data-preview-version]').forEach(b=>b.onclick=async()=>{try{const v=await api(base(c.p.id)+'/history/'+b.dataset.previewVersion);modal('Review version '+v.version,`<p>Restoring brings back the title, notes, scene order and prose from this version. Current work is saved as version ${c.p.version}.</p><details><summary>Read the manuscript from this version</summary><pre class="fiction-version-text">${esc(assembleStory(v.work))}</pre></details><details><summary>Read its planning notes</summary><pre class="fiction-version-text">${esc(JSON.stringify(v.work.lessons,null,2))}</pre></details><button class="btn" id="fiction-restore-version">Restore as a new draft</button>`);$('#fiction-restore-version').onclick=async()=>{try{await api(base(c.p.id)+'/restore',{base_version:c.p.version,version:v.version});$('#modal').close();clearLocal(c.p.id);await render(c.p.id,c.serial,new URLSearchParams('view='+c.view+'&step='+c.stage.id))}catch(e){toast(e.message)}}}catch(e){toast(e.message)}});
  }catch(e){toast(e.message)}
 }
 async function leave(){clearTimeout(timer);clearTimeout(poll);const c=ctx;if(c?.dirty)await save(c);if(ctx===c)ctx=null;}
 window.addEventListener('beforeunload',event=>{if(ctx?.dirty){keepLocal(ctx);event.preventDefault();event.returnValue=''}});
 return {render,leave};
}
