import {createWorkbenchUI} from './workbench.js';
export function createPaperUI({api,esc,heading,list,toast,modal,teachingUI,getState,isCurrent,refresh}) {
 const $=s=>document.querySelector(s);
 const targetLink=id=>'#paper/'+encodeURIComponent(id);
 const exerciseLink=key=>'#practice/'+encodeURIComponent(key);
 const words=text=>text.trim().split(/\s+/).filter(Boolean).length;
 let paperData=null,cardCache=null;
 async function data(){paperData=await api('/paper');return paperData}
 function reading(books){return books.map(b=>`<div class="reading-entry"><a href="/api/paper/readings/${esc(b.id)}" target="_blank" rel="noreferrer">${esc(b.title)}</a><p>${esc(b.principle)}</p><small>${esc(b.reading)}</small></div>`).join('')}
 function warning(text){return `<p class="tiny">${esc(text)}</p>`}
 async function sourceCard(id){
  const [c,r]=await Promise.all([api('/paper/cards/'+encodeURIComponent(id)),api('/reader-reviews/'+encodeURIComponent(id))]);
  modal('Archived idea card: '+c.id,`<p class="text-role source">Archived notes · read only</p><p class="tiny">${c.in_paper?'Marked as used in the archive':'Alternative card in the archive'} · ${esc(c.source_type)}. This archive may contain LLM-written notes. It is not the uploaded manuscript and is not automatically agreed text. Check its ideas and cited evidence.</p><p class="source-path tiny">${esc(c.archive_path)}</p><details open><summary>Read the archived wording and notes</summary><pre class="source-text">${esc(c.raw)}</pre></details><details><summary>AI-assisted reader review · suggestions to consider</summary>${teachingUI.reviewHTML(r)}</details><p class="tiny">Citation keys in this card: ${esc(c.citation_keys.join(', ')||'None recorded')}. Their presence does not mean the cited papers have been checked.</p>`);
 }
 async function chooseSources(n,p){
  cardCache ||= await api('/paper/cards');
  let selected=new Set(p.state.nodes[n.id]?.source_ids||[]);
  modal('Choose source cards for '+n.id,`<p>Choose cards whose ideas you want to use. The suggested matches use topic overlap and may follow an older argument. Read them before deciding.</p><label class="field">Find a card<input id="card-search" type="search" placeholder="Title, key or section…"></label><label class="checkbox-row"><input id="cards-used" type="checkbox">Only cards marked as used in the archive</label><p id="card-selection-count" class="tiny"></p><div id="card-options" class="card-picker"></div><button class="btn" id="save-card-selection">Save my source selection</button>`);
  function draw(){
   const q=$('#card-search').value.toLowerCase(),used=$('#cards-used').checked;
   const filtered=cardCache.filter(c=>(!used||c.in_paper)&&(c.id+' '+c.title+' '+c.section_title).toLowerCase().includes(q));
   filtered.sort((a,b)=>(selected.has(b.id)-selected.has(a.id))||(n.source_card_ids.includes(b.id)-n.source_card_ids.includes(a.id))||a.id.localeCompare(b.id));
   $('#card-selection-count').textContent=`${selected.size}/12 selected · ${filtered.length} matching cards`;
   $('#card-options').innerHTML=filtered.slice(0,60).map(c=>`<div class="source-option"><label class="checkbox-row"><input type="checkbox" data-pick-card="${esc(c.id)}" ${selected.has(c.id)?'checked':''}><span><strong>${esc(c.id)}</strong><small>${esc(c.title)}</small></span></label><button class="btn quiet" data-preview-card="${esc(c.id)}">Read</button><pre class="source-text hidden" id="preview-${esc(c.id)}"></pre></div>`).join('')+warning(filtered.length>60?'Showing the first 60 matches. Narrow the search to find another card.':'');
   document.querySelectorAll('[data-pick-card]').forEach(e=>e.onchange=()=>{if(e.checked&&selected.size>=12){e.checked=false;toast('Choose up to twelve source cards.');return}if(e.checked)selected.add(e.dataset.pickCard);else selected.delete(e.dataset.pickCard);$('#card-selection-count').textContent=`${selected.size}/12 selected · ${filtered.length} matching cards`});
   document.querySelectorAll('[data-preview-card]').forEach(e=>e.onclick=async()=>{try{const c=await api('/paper/cards/'+encodeURIComponent(e.dataset.previewCard)),area=document.getElementById('preview-'+c.id);area.textContent=c.raw;area.classList.toggle('hidden')}catch(error){toast(error.message)}});
  }
  $('#card-search').oninput=draw;$('#cards-used').onchange=draw;draw();
  $('#save-card-selection').onclick=async()=>{try{await api('/paper/nodes/'+n.id,{base_version:p.state.version,source_ids:[...selected]},'PUT');$('#modal').close();await render(n.id);toast('Your source selection is saved. Record the checked ideas in your writing outline.')}catch(e){toast(e.message)}};
 }
 async function selectAttempt(nodeId,attempts,onSelected){
  const p=await data(),n=p.blueprint.nodes.find(n=>n.id===nodeId);
  if(!attempts.length){toast('Save your paragraph attempt first.');return}
  modal('Select a version for your paper',`<p>This selects one saved attempt for <strong>${esc(n.title)}</strong>. Later edits remain separate until you select them.</p><label class="field">Saved version<select id="paper-attempt">${[...attempts].reverse().map((a,i)=>`<option value="${esc(a.id)}">${i===0?'Latest attempt':'Earlier attempt'} · ${new Date(a.created).toLocaleString()} · ${words(a.text)} words</option>`).join('')}</select></label><div id="selected-attempt-preview" class="history-text"></div><label class="checkbox-row"><input id="reviewed-selection" type="checkbox">I reviewed this saved text, its ideas and any evidence still needed.</label><button id="commit-paper-attempt" class="btn">Use this saved version in my paper</button><p id="paper-select-error" role="status"></p>`);
  const preview=()=>{$('#selected-attempt-preview').textContent=attempts.find(a=>a.id===$('#paper-attempt').value).text;$('#reviewed-selection').checked=false};
  $('#paper-attempt').onchange=preview;preview();
  $('#commit-paper-attempt').onclick=async()=>{try{await api('/paper/nodes/'+nodeId,{base_version:p.state.version,attempt_id:$('#paper-attempt').value,confirmed:$('#reviewed-selection').checked},'PUT');$('#modal').close();toast('Your selected paragraph is now in My WISE paper.');if(onSelected)await onSelected()}catch(e){if($('#paper-select-error'))$('#paper-select-error').textContent=e.message;else toast(e.message)}};
 }
 const workbench=createWorkbenchUI({api,esc,toast,modal,getState,isCurrent,data,sourceCard,chooseSources,selectAttempt,teachingUI,refresh});
 async function render(id,serial){return workbench.render(id,serial)}
 function catalogue(){
  const s=getState(),available=s.exercises.filter(e=>!e.archived_version);let page=0;
  const topics=new Map(available.map(e=>[e.topic_id,{title:e.topic_title,goal:e.topic_goal||''}]));
  const levels={foundation:{title:'Foundation',description:'Recognise patterns and construct accurate sentences with supplied choices.'},developing:{title:'Developing',description:'Explain relations, qualify claims and build short paragraphs with some guidance.'},advanced:{title:'Advanced',description:'Diagnose meaning and write connected prose from supplied evidence.'},stretch:{title:'Stretch',description:'Judge proposed revisions, compress complex claims and justify your editorial decisions. This is a task challenge, not a CEFR rating.'}};
  $('#main').innerHTML=heading('Practise the English your research needs.','Choose a difficulty, a research topic and the language skill you want to learn.', '<a class="btn" href="#paper">Build my WISE paper</a>')+`
   <section class="card advanced-callout"><span class="tag">READY FOR MORE?</span><h2>Write, judge and revise at a higher level</h2><p>384 new Advanced and Stretch activities · 8 courses · 32 modules. Work through 96 cases using four different writing tasks.</p><div class="actions"><a class="btn" href="#courses/advanced">Explore advanced English →</a><a class="btn secondary" href="#phrasebook">Use the academic phrasebook</a></div></section><section class="card"><div class="catalogue-filters">
   <label class="field">Find an exercise<input id="exercise-query" type="search" placeholder="e.g. guardrails, articles, evidence…"></label>
   <label class="field">Difficulty<select id="exercise-difficulty"><option value="">All difficulty levels</option>${Object.entries(levels).map(([id,l])=>`<option value="${id}">${l.title}</option>`).join('')}</select></label>
   <label class="field">Research topic<select id="exercise-topic"><option value="">All research topics</option>${[...topics].sort((a,b)=>a[1].title.localeCompare(b[1].title)).map(([id,t])=>`<option value="${esc(id)}">${esc(t.title)}</option>`).join('')}</select></label>
   <label class="field">English skill<select id="exercise-skill"><option value="">All skills</option>${Object.entries(s.skills).map(([id,title])=>`<option value="${id}">${esc(title)}</option>`).join('')}</select></label>
   <label class="field">Paper section<select id="exercise-section"><option value="">All sections and topics</option><option value="english">Academic English</option>${['I','II','III','IV','V','VI','AB'].map(x=>`<option>${x}</option>`).join('')}</select></label>
   <label class="field">Practice stage<select id="exercise-level"><option value="">All stages</option>${['guided','open_sentence','short_argument','fresh_prose','transfer'].map(x=>`<option value="${x}">${x.replaceAll('_',' ')}</option>`).join('')}</select></label>
   <label class="field">My work<select id="exercise-progress"><option value="">All exercises</option><option value="new">Not yet attempted</option><option value="saved">With saved attempts</option><option value="complete">Completed activities</option></select></label></div>
   <div id="learning-focus" class="learning-focus" aria-live="polite"></div><div class="section-row"><p id="exercise-results-count" role="status"></p><button class="btn quiet" id="reset-exercise-filters">Clear filters</button></div></section>
   <div id="exercise-results" class="grid catalogue-grid"></div><div class="actions"><button class="btn secondary" id="catalogue-prev">Previous</button><span id="catalogue-page"></span><button class="btn secondary" id="catalogue-next">Next</button></div>`;
  const filters=['exercise-query','exercise-difficulty','exercise-topic','exercise-skill','exercise-section','exercise-level','exercise-progress'];
  function draw(){
   const q=$('#exercise-query').value.toLowerCase(),skill=$('#exercise-skill').value,section=$('#exercise-section').value,level=$('#exercise-level').value,progress=$('#exercise-progress').value,difficulty=$('#exercise-difficulty').value,topic=$('#exercise-topic').value;
   const matches=available.filter(e=>{const done=!!s.learning?.exercise_status[e.key]?.completed,attempted=s.sessions.some(a=>a.exercise_id===e.key&&a.attempts);return (!q||(e.title+' '+e.prompt+' '+(e.paper_node_id||'')+' '+e.topic_title+' '+(e.learning_objective||'')).toLowerCase().includes(q))&&(!difficulty||e.difficulty===difficulty)&&(!topic||e.topic_id===topic)&&(!skill||e.skill_ids.includes(skill))&&(!section||(section==='english'?(e.id.startsWith('AWL-EN-')||e.id.startsWith('AWL-ADV-')):e.paper_section===section))&&(!level||e.level===level)&&(!progress||(progress==='complete'?done:progress==='saved'?attempted:!attempted))});
   const pages=Math.max(1,Math.ceil(matches.length/24));page=Math.min(page,pages-1);
   $('#exercise-results-count').textContent=`${matches.length} matching exercises · ${available.length} available in total`;
   $('#learning-focus').innerHTML=`<strong>${difficulty?levels[difficulty].title+' practice':'Choose the support you need'}</strong><p>${esc(difficulty?levels[difficulty].description:'Foundation: sentence patterns. Developing: explain and connect ideas. Advanced: synthesise and write independently. These are task difficulty levels, not proficiency scores.')}</p>${topic&&topics.get(topic).goal?`<p><strong>In this topic you learn:</strong> ${esc(topics.get(topic).goal)}</p>`:''}`;
   $('#exercise-results').innerHTML=matches.slice(page*24,(page+1)*24).map(e=>`<a class="card catalogue-card" href="${exerciseLink(e.key)}"><div class="catalogue-tags"><span class="tag difficulty-${esc(e.difficulty)}">${esc(e.difficulty_label)}</span><span class="tag neutral">${esc(e.paper_node_id||e.topic_title||'Starter practice')}</span></div><p class="completion-state ${s.learning?.exercise_status[e.key]?.completed?'complete':''}">${s.learning?.exercise_status[e.key]?.status==='correct'?'✓ Correct':s.learning?.exercise_status[e.key]?.status==='tutor_met'?'✓ Tutor criteria met':s.learning?.exercise_status[e.key]?.status==='reviewed'?'✓ Reviewed by you':s.learning?.exercise_status[e.key]?.attempts?'◐ In progress':'○ Not started'}</p><h3>${esc(e.title)}</h3>${e.paper_node_id&&e.prompt.startsWith('Target: ')?`<p>${esc(e.prompt.split('\n')[0].replace(/^Target: /,''))}</p>`:''}<p>${esc((e.level||'practice').replaceAll('_',' '))}</p><small>${esc(e.skill_ids.map(id=>s.skills[id]).join(' · '))}</small></a>`).join('')||'<p class="empty">No matching exercises. Try fewer filters or choose Clear filters.</p>';
   $('#catalogue-page').textContent=`Page ${page+1} of ${pages}`;$('#catalogue-prev').disabled=page===0;$('#catalogue-next').disabled=page===pages-1;
  }
  for(const id of filters)$('#'+id).oninput=()=>{page=0;draw()};
  $('#reset-exercise-filters').onclick=()=>{for(const id of filters)$('#'+id).value='';page=0;draw()};
  $('#catalogue-prev').onclick=()=>{page--;draw();$('#exercise-results').scrollIntoView({behavior:'smooth'})};
  $('#catalogue-next').onclick=()=>{page++;draw();$('#exercise-results').scrollIntoView({behavior:'smooth'})};draw();
 }
 async function enhancePractice(e,context){
  const target=context.returnNode||e.paper_node_id;if(!target)return;
  const area=document.createElement('div');area.className='paper-practice-link';
  area.innerHTML=`<a href="${targetLink(target)}">← ${context.returnNode?'Return to my WISE paragraph':'Open the WISE paragraph desk'} · ${esc(target)}</a>${e.paper_draft?'<button class="btn secondary" id="select-paper-version">Use a saved version in my paper</button>':''}`;
  $('.exercise-body').prepend(area);
  if(e.paper_draft)$('#select-paper-version').onclick=()=>selectAttempt(e.paper_node_id,context.session.attempts).catch(e=>toast(e.message));
 }
 return {render,catalogue,enhancePractice};
}
