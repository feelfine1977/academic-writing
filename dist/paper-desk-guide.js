// Read-only guidance views over existing note fields. The manuscript and editable
// planning fields stay mounted while the reader changes topic or example.
import {renderPaperMarkdown,paperLinkResolver,safeReadingURL} from './paper-markdown.js';
const escapeHTML=(s='')=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function splitGuidance(value){
 const lines=String(value||'').replace(/\r\n?/g,'\n').split('\n');let intro=[],sections=[],current=intro,fence=null;
 for(const line of lines){
  const code=line.match(/^\s*(`{3,}|~{3,})/);
  if(code){if(!fence)fence=code[1][0];else if(fence===code[1][0])fence=null;current.push(line);continue}
  const heading=!fence&&line.match(/^###\s+(.+?)\s*#*\s*$/);
  if(heading){const section={title:heading[1],lines:[]};sections.push(section);current=section.lines}else current.push(line);
 }
 return {intro:intro.join('\n').trim(),sections:sections.map(s=>({title:s.title,body:s.lines.join('\n').trim()}))};
}
export function guidanceModel(fields={}){
 const opening=splitGuidance(fields['Opening options']);
 const isOption=s=>/^\d+\s*[·.:—–-]\s|^A very short|^Very short/i.test(s.title);
 const options=opening.sections.filter(isOption),extra=opening.sections.filter(s=>!isOption(s));
 const flow=splitGuidance(fields['Flow and wording notes']);
 const reviewer=splitGuidance(fields['Academic reviewer guidance']);
 const meeting=splitGuidance(fields['Supervisor comments and editing consequences']);
 const topics=[];
 if(options.length)topics.push({id:'opening-options',label:'Opening options',kind:'options'});
 else if(fields['Opening options']?.trim())topics.push({id:'opening-full',label:'Opening options',body:fields['Opening options']});
 const labels={'Begin this part':'Begin this part','End this part':'End this part','Useful vocabulary':'Vocabulary','In your current draft':'Feedback on the reviewed draft'};
 flow.sections.forEach((s,i)=>topics.push({id:'flow-'+i,label:labels[s.title]||s.title,body:s.body,intro:flow.intro}));
 if(!flow.sections.length&&fields['Flow and wording notes']?.trim())topics.push({id:'flow-full',label:'Beginnings, endings & wording',body:fields['Flow and wording notes']});
 reviewer.sections.forEach((s,i)=>topics.push({id:'review-'+i,label:s.title,body:s.body,intro:reviewer.intro}));
 if(!reviewer.sections.length&&fields['Academic reviewer guidance']?.trim())topics.push({id:'review-full',label:'Reviewer tips',body:fields['Academic reviewer guidance']});
 const sourceExtras=extra.filter(s=>/source|citation|passage/i.test(s.title));
 const contextExtras=extra.filter(s=>!sourceExtras.includes(s));
 return {topics,options,openingIntro:opening.intro,sourceExtras,contextExtras,meeting};
}
export function guidancePreview(fields={}){
 const value=String(fields['Main message']||fields.Purpose||'Choose the support you need for this writing part.').replace(/\s+/g,' ').trim();
 if(value.length<=220)return value;
 return value.slice(0,217).replace(/\s+\S*$/,'')+'…';
}
function renderSections(sections,rich){return sections.map(s=>`<h3>${escapeHTML(s.title)}</h3>${rich(s.body)}`).join('')}
export function deskGuideHTML(note,plan,{editable=true}={}){
 const f=note.fields||{},m=guidanceModel(f),esc=escapeHTML,rich=s=>renderPaperMarkdown(s,{resolve:paperLinkResolver(note,plan)});
 if(!editable&&!m.topics.length&&!f['Supervisor comments and editing consequences']&&!f['Notes and bullet points'])return '';
 const select=(label,id,items)=>`<label class="desk-guide-choice">${esc(label)}<select id="${id}">${items.map(t=>`<option value="${esc(t.id)}">${esc(t.label)}</option>`).join('')}</select></label>`;
 const button=(page,title,description)=>`<button type="button" class="desk-guide-destination" data-guide-go="${page}"><span>${esc(title)}</span><small>${esc(description)}</small><b aria-hidden="true">›</b></button>`;
 const page=(id,content)=>`<section data-guide-page="${id}" ${id!=='home'?'hidden':''}>${content}</section>`;
 const meetingChoices=m.meeting.sections.map((s,i)=>({id:String(i),label:s.title}));
 const meetingBody=meetingChoices.length?`${select('Read meeting guidance','desk-guide-meeting-choice',meetingChoices)}${m.meeting.sections.map((s,i)=>`<div data-guide-meeting="${i}" ${i?'hidden':''} class="paper-markdown">${rich(s.body)}</div>`).join('')}${m.meeting.intro?`<details><summary>About these meeting notes</summary><div class="paper-markdown">${rich(m.meeting.intro)}</div></details>`:''}`:`<div class="paper-markdown">${rich(f['Supervisor comments and editing consequences']||'No meeting guidance is attached to this part.')}</div>`;
 const optionList=m.options.map((s,i)=>({id:String(i),label:s.title}));
 const openingBody=`${select('Read one opening','desk-guide-option-choice',optionList)}<p class="desk-guide-small">Optional wording to adapt. Viewing an option does not change your draft.</p>${m.options.map((s,i)=>`<div data-guide-option="${i}" ${i?'hidden':''} class="paper-markdown">${rich(s.body)}</div>`).join('')}<div class="desk-guide-extra-links">${m.sourceExtras.length?'<button class="btn quiet" data-guide-go="opening-sources">Sources & context →</button>':''}${m.contextExtras.length||m.openingIntro?'<button class="btn quiet" data-guide-go="opening-context">Why these options? →</button>':''}</div>`;
 const helpBody=m.topics.length?`${select('What would help now?','desk-guide-topic-choice',m.topics)}${m.topics.map((t,i)=>`<div data-guide-topic="${esc(t.id)}" ${i?'hidden':''}>${t.kind==='options'?openingBody:`<p class="desk-guide-small">Prepared writing guidance · examples are not source quotations. Use Tutor for feedback on your latest draft.</p>${/\[(?:evaluation setting|observed result)\]/i.test(t.body)?'<p class="desk-guide-placeholder">Bracketed settings and results are placeholders. Fill them only from your completed evaluation.</p>':''}<div class="paper-markdown">${rich(t.body)}</div>${t.intro?`<details><summary>About this guidance</summary><div class="paper-markdown">${rich(t.intro)}</div></details>`:''}`}</div>`).join('')}`:'<p>No writing guidance is attached yet. Use My notes for your own reminders.</p>';
 const noteFields=['Notes and bullet points','Reasoning and decisions','Next step'];
 const notes=noteFields.map(name=>`<label class="field">${esc(name)}<textarea data-paper-field="${esc(name)}" rows="${name==='Notes and bullet points'?8:4}">${esc(f[name]||'')}</textarea></label>`).join('');
 return `<div class="desk-plan-guide" id="desk-plan-guide"><header class="desk-guide-heading"><button class="btn quiet" id="desk-guide-back" hidden>← Back to Plan</button><h2 id="desk-guide-title" tabindex="-1">Plan for this part</h2>${editable?'<button class="btn quiet desk-guide-return" id="desk-guide-return">Return to my draft</button>':''}</header>${page('home',`<p class="desk-guide-orientation">${esc(guidancePreview(f))}</p><nav class="desk-guide-destinations" aria-label="Choose writing support">${button('plan','This part’s plan','Purpose, bullet points and scope')}${m.topics.length?button('writing','Writing help',m.options.length?'Opening options, endings and vocabulary':'Beginnings, endings and vocabulary'):''}${f['Supervisor comments and editing consequences']?button('meeting','Meeting guidance','General guidance and remarks for this part'):''}${editable?button('notes','My notes','Your bullet points, reasoning and next step'):''}</nav><p class="desk-guide-small">Choose one. Your draft stays here.</p>${safeReadingURL(note.uri)?`<a class="desk-guide-full-note" href="${esc(safeReadingURL(note.uri))}">Full note in Obsidian ↗</a>`:''}`)}${page('plan',`<div class="paper-markdown">${f.Purpose?'<h3>Purpose</h3>'+rich(f.Purpose):''}${f['Main message']?'<h3>Main point</h3>'+rich(f['Main message']):''}<h3>Bullet points</h3><div id="desk-guide-bullets">${rich(f['Notes and bullet points']||'No bullet points yet.')}</div></div>${f['Scope and boundaries']?`<details><summary>Scope and boundaries</summary><div class="paper-markdown">${rich(f['Scope and boundaries'])}</div></details>`:''}${editable?'<button class="btn quiet" data-guide-go="notes">Edit my planning notes →</button>':''}`)}${page('writing',helpBody)}${page('meeting',`<p class="desk-guide-small">Meeting remarks and their recorded interpretation. Keep source wording and proposed consequences distinct.</p>${meetingBody}`)}${editable?page('notes',notes):''}${page('opening-sources',`<div class="paper-markdown">${renderSections(m.sourceExtras,rich)}</div>`)}${page('opening-context',`<div class="paper-markdown">${rich(m.openingIntro)}${renderSections(m.contextExtras,rich)}</div>`)}</div>`;
}
export function mountDeskGuide({host,note,plan,editor,onReference,current=()=>true}){
 if(!host)return {dispose(){}};
 const abort=new AbortController(),q=s=>host.querySelector(s),all=s=>[...host.querySelectorAll(s)],rich=s=>renderPaperMarkdown(s,{resolve:paperLinkResolver(note,plan)});
 const scroller=host.closest('.desk-panel')||host.closest('.desk-project-home')||host;
 const titles={home:'Plan for this part',plan:'This part’s plan',writing:'Writing help',meeting:'Meeting guidance',notes:'My notes','opening-sources':'Sources & context','opening-context':'Why these options?'};
 const scrolls=new Map(),invokers=new Map();let page='home',generation=0,selection=editor?[editor.selectionStart,editor.selectionEnd,editor.selectionDirection]:null,editorScroll=editor?.scrollTop||0;
 const rememberEditor=()=>{selection=[editor.selectionStart,editor.selectionEnd,editor.selectionDirection];editorScroll=editor.scrollTop};
 if(editor){for(const event of ['input','select','blur'])editor.addEventListener(event,rememberEditor,{signal:abort.signal});q('#desk-guide-return')?.addEventListener('click',()=>{editor.focus({preventScroll:true});editor.setSelectionRange(...selection);editor.scrollTop=editorScroll;if(matchMedia('(max-width:760px)').matches)editor.scrollIntoView({block:'nearest'})},{signal:abort.signal})}
 const scrollKey=()=>[page,q('#desk-guide-topic-choice')?.value,q('#desk-guide-option-choice')?.value,q('#desk-guide-meeting-choice')?.value].join('|');
 const remember=()=>scrolls.set(scrollKey(),scroller.scrollTop);
 const restore=()=>{scroller.scrollTop=scrolls.get(scrollKey())||0};
 function showPage(next,{focus=true}={}){
  if(!current()||!q(`[data-guide-page="${next}"]`))return;
  remember();generation++;page=next;all('[data-guide-page]').forEach(e=>e.hidden=e.dataset.guidePage!==next);
  q('#desk-guide-title').textContent=titles[next];q('#desk-guide-back').hidden=next==='home';q('#desk-guide-back').textContent=next.startsWith('opening-')?'← Back to openings':'← Back to Plan';
  if(next==='plan'){
   const value=q('[data-paper-field="Notes and bullet points"]')?.value;
   if(value!==undefined)q('#desk-guide-bullets').innerHTML=rich(value||'No bullet points yet.');
  }
  restore();if(focus)q('#desk-guide-title').focus({preventScroll:true});
 }
 function choose(select,selector,key){
  if(!select)return;let old=select.value;
  select.addEventListener('change',()=>{
   // Changing a select precedes its event: remember the old view explicitly.
   generation++;const next=select.value;select.value=old;remember();select.value=next;old=next;
   all(selector).forEach(e=>e.hidden=e.dataset[key]!==next);restore();
  },{signal:abort.signal});
 }
 q('#desk-guide-back').addEventListener('click',()=>{const target=page.startsWith('opening-')?'writing':'home';showPage(target,{focus:false});(invokers.get(target)||q('#desk-guide-title')).focus({preventScroll:true})},{signal:abort.signal});
 host.addEventListener('click',e=>{
  const button=e.target.closest('[data-guide-go]');if(button&&host.contains(button)){invokers.set(page,button);showPage(button.dataset.guideGo);return}
  const a=e.target.closest('a');if(a&&onReference){const version=generation;onReference(e,a,{page,stillReading:()=>current()&&version===generation})}
 },{signal:abort.signal});
 choose(q('#desk-guide-topic-choice'),'[data-guide-topic]','guideTopic');
 choose(q('#desk-guide-option-choice'),'[data-guide-option]','guideOption');
 choose(q('#desk-guide-meeting-choice'),'[data-guide-meeting]','guideMeeting');
 return {showPage,dispose(){generation++;abort.abort()}};
}
