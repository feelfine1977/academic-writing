// Function-first reading support. Patterns and examples never become manuscript text automatically.
export function createPhrasebookUI({api,esc,toast,isCurrent}) {
 const read=key=>{try{return localStorage.getItem(key)||''}catch{return ''}};
 const write=(key,text)=>{try{localStorage.setItem(key,text);return true}catch{return false}};
 const defaults={I:'premises',II:'gap',III:'conditions',IV:'definitions',V:'results',VI:'limitations',AB:'abstract'};
 async function mount(container,nodeId,isActive=()=>true,onInsert=null,moveId=null){
  const r=await api('/teaching/phrasebook'+(nodeId?'?node_id='+encodeURIComponent(nodeId):''));if(!isActive()||!container.isConnected)return;
  const $=selector=>container.querySelector(selector),section=nodeId?.split('-')[0];
  let selected=moveId||defaults[section]||'problem';
  const moves=[...r.moves].sort((a,b)=>Number(b.suggested)-Number(a.suggested));
  container.innerHTML=`<div class="phrasebook-heading"><span class="tag">MEANING → PATTERN → YOUR SENTENCE</span><h3>Find language for this argument move</h3><p>${esc(r.note)}</p></div>${nodeId?`<p><strong>This paragraph:</strong> ${esc(r.purpose)}</p>`:''}<div class="phrasebook-controls"><label class="field">Find a purpose<input type="search" data-phrase-search placeholder="e.g. concession, methods, gap, evidence"></label><label class="field">What should the sentence do?<select data-phrase-select></select></label></div><p class="tiny" data-phrase-count role="status"></p><div data-phrase-body></div>`;
  function options(){
   const q=$('[data-phrase-search]').value.toLowerCase();const filtered=moves.filter(m=>[m.title,m.purpose,m.pattern,m.rule,m.wise].join(' ').toLowerCase().includes(q));
   $('[data-phrase-select]').innerHTML=filtered.map(m=>`<option value="${esc(m.id)}">${m.suggested?'For this section · ':''}${esc(m.title)}</option>`).join('');
   if(filtered.some(m=>m.id===selected))$('[data-phrase-select]').value=selected;else selected=filtered[0]?.id;
   $('[data-phrase-count]').textContent=`${filtered.length} of ${moves.length} writing purposes. Section suggestions are starting points; choose the move your argument needs.`;
   show();
  }
  function show(){
   selected=$('[data-phrase-select]').value;const m=moves.find(m=>m.id===selected),body=$('[data-phrase-body]');
   if(!m){body.innerHTML='<p>No matching purpose. Try a broader word or clear the search.</p>';return}
   const link='#practice/'+encodeURIComponent(m.practice_key)+(nodeId?'?from='+encodeURIComponent(nodeId):'');
   const key='awl-phrase-sentence-'+(nodeId||'notebook')+'-'+m.id;
   body.innerHTML=`<h4>${esc(m.purpose)}</h4><div class="phrase-pattern">${esc(m.pattern)}</div><p>${esc(m.rule)}</p><div class="note-strip"><strong>Check before using it</strong><p>${esc(m.watch)}</p></div>${m.wise?`<details><summary>Research application example · WISE</summary><p>${esc(m.wise)}</p></details>`:''}${r.boundary?`<p class="tiny"><strong>Keep this paragraph's boundary:</strong> ${esc(r.boundary)}</p>`:''}<details class="phrase-example"><summary>Worked example · ${esc(m.example.subject)}</summary><p>${esc(m.example.facts)}</p><blockquote class="prose">${esc(m.example.text)}</blockquote><p>${esc(m.example.why)}</p><small>Original constructed illustration. Its facts belong to this example.</small></details><label class="field">Try your own sentence<textarea data-phrase-sentence rows="3" maxlength="3000" placeholder="State your point and its evidence in your own words. Adapt the pattern only if it expresses that relationship."></textarea></label><p class="tiny" data-phrase-saved role="status">Draft stored in this browser; add it to your paragraph and save a version to include it in backups.</p><div class="actions">${onInsert?'<button class="btn secondary" data-phrase-insert>Add my sentence to my paragraph</button>':''}<a class="btn" data-phrase-practice href="${link}">Practise this move${nodeId?', then return':''} →</a></div><p class="phrase-reading"><a href="${esc(m.reading.url)}" target="_blank" rel="noreferrer">Read ${esc(m.reading.title)} · PDF p. ${m.reading.page}${m.reading.end_page!==m.reading.page?'–'+m.reading.end_page:''}</a><br><a href="/api/paper/readings/PHRASEBANK#page=4" target="_blank" rel="noreferrer">Academic Phrasebank · full contents</a> · <a href="#courses/${encodeURIComponent(m.module_id)}">See this module</a></p>`;
   const input=$('[data-phrase-sentence]');input.value=read(key);
   input.oninput=()=>{$('[data-phrase-saved]').textContent=write(key,input.value)?'Your sentence draft is kept in this browser. Save an argument version after adding it to your paper.':'Browser storage is unavailable; copy your sentence into the paragraph and save a version.'};
   if(onInsert)$('[data-phrase-insert]').onclick=()=>{if(!input.value.trim()){input.focus();$('[data-phrase-saved]').textContent='Write your own sentence first.';return}onInsert(input.value);toast('Your sentence was added. Read it in context, then save a paragraph version.');};
  }
  $('[data-phrase-search]').oninput=options;$('[data-phrase-select]').onchange=show;options();
 }
 async function render(id,serial){
  const container=document.querySelector('#main');container.innerHTML='<div class="page-heading"><div><div class="eyebrow">Academic English in use</div><h1>A phrase has a job.</h1><p class="subtitle">Decide what you mean, choose a pattern and write your own sentence.</p></div><a class="btn secondary" href="#courses/advanced">Advanced English courses</a></div><section class="card" id="phrasebook-page"></section>';
  await mount(document.querySelector('#phrasebook-page'),null,()=>isCurrent(serial),null,id);
 }
 return {mount,render};
}
