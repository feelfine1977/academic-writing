import {paperRoute,flowNeighbours,sectionFor} from './paper-flow.js';
import {renderPaperMarkdown,paperLinkResolver} from './paper-markdown.js';
import {mountDeskReferences} from './paper-desk-references.js';
import {mountPaperDeskTutor} from './paper-desk-tutor.js';
import {readingContextShell,mountReadingContext} from './paper-desk-context.js';
import {deskGuideHTML,mountDeskGuide} from './paper-desk-guide.js';
import {deskOutlineHTML,mountDeskOutline,SUPPORT_TABS,nextSupportTab} from './paper-desk-outline.js';

export const deskTitle=t=>String(t||'').replace(/^L\d+[-–][A-Z0-9-]+\s*[·:]\s*/,'').replace(/\s*[—–]\s*meeting draft$/i,'');
export function deskSections(plan){return plan.nodes.filter(n=>n.type==='section'&&!n.parent_id)}
export function deskArguments(plan,scope='all'){
 return plan.nodes.filter(n=>n.type==='argument'&&(scope==='all'||sectionFor(plan,n.id)===scope));
}
const stored=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}};
const keep=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value))}catch{}};
const words=s=>String(s||'').trim().split(/\s+/).filter(Boolean).length;

export function createPaperDeskUI({api,esc,modal,toast}){
 const $=s=>document.querySelector(s);
 const rich=(s,n,p)=>renderPaperMarkdown(s,{resolve:paperLinkResolver(n,p)});
 function shell(plan,note){
  const writing=note.type==='argument',sections=deskSections(plan),root=sections.find(n=>n.id===sectionFor(plan,note.id));
  return `<div class="desk-app" data-paper-desk><header class="desk-toolbar"><div class="desk-toolbar-left"><a href="#papers" class="desk-home" aria-label="Back to Papers">Writing Lab</a><button class="btn quiet" id="desk-outline-toggle" aria-expanded="false" aria-controls="${writing?'desk-reading-context':'desk-outline'}">☰ Paper outline</button><span class="desk-section-name">${esc(deskTitle(root?.title||plan.title))}</span></div><div class="desk-toolbar-right"><button class="btn secondary" id="desk-export">Export approved text</button><details class="desk-more"><summary>More</summary><div class="desk-more-menu"><button class="btn quiet" id="desk-planning">Planning tools & all notes</button><button class="btn quiet" id="desk-timer">Show / hide timer</button><button class="btn quiet" id="paper-compare">Compare & recover</button><a href="${esc(note.uri)}" class="btn quiet">Open this note in Obsidian</a><a href="/guide.html" id="desk-help" class="btn quiet">How this writing view works</a></div></details></div></header>${!writing?'<nav class="desk-outline" id="desk-outline" aria-label="Paper outline" hidden></nav>':''}${writing?`<div class="desk-body" id="desk-body">${readingContextShell()}<section class="desk-writing" aria-label="Writing area"><div class="desk-argument-heading"><div class="desk-part-step"><span id="desk-step"></span><span class="tag" id="paper-writing-state">${note.writing_status==='complete'?'✓ Approved for export':note.fields['Manuscript prose']?.trim()?'Draft saved':'Ready to write'}</span></div><h1>${esc(deskTitle(note.title))}</h1><div class="desk-context-tools" aria-label="Read while writing"><button class="btn quiet" id="desk-previous" aria-expanded="false" aria-controls="desk-reading-context">← Read previous part</button>${root?`<a class="btn quiet" href="#section-writing/${encodeURIComponent(plan.id)}?section=${encodeURIComponent(root.id)}">Write whole section</a>`:''}<button class="btn quiet" id="desk-context-outline" aria-expanded="false" aria-controls="desk-reading-context">Paper outline</button></div><details class="desk-purpose"><summary>Purpose of this part</summary><p>${esc(note.fields.Purpose||note.fields['Main message']||'Develop the argument in your own words.')}</p></details></div><label class="paper-field desk-manuscript">Manuscript prose<textarea data-paper-field="Manuscript prose" class="editor" id="desk-manuscript" placeholder="Write this part in your own words…" spellcheck="true">${esc(note.fields['Manuscript prose']||'')}</textarea></label><div class="desk-editor-meta"><span id="desk-word-count">${words(note.fields['Manuscript prose'])} words</span><span>Citations stay as editable LaTeX.</span></div><div id="desk-cited-sources" hidden></div></section><aside class="desk-companion" id="desk-companion" aria-label="Writing support"><div class="desk-panel-tabs" role="tablist" aria-label="Writing support"><button role="tab" class="btn quiet" id="desk-tab-references" data-desk-tab="references" aria-controls="desk-panel-references" aria-selected="true">References</button><button role="tab" class="btn quiet" id="desk-tab-plan" data-desk-tab="plan" aria-controls="desk-panel-plan" aria-selected="false" tabindex="-1">Plan</button><button role="tab" class="btn quiet" id="desk-tab-tutor" data-desk-tab="tutor" aria-controls="desk-panel-tutor" aria-selected="false" tabindex="-1">Tutor</button><button role="tab" class="btn quiet" id="desk-tab-outline" data-desk-tab="outline" aria-controls="desk-panel-outline" aria-selected="false" tabindex="-1">Outline</button><button class="btn quiet desk-hide-support" id="desk-hide-support" aria-label="Hide support panel">×</button></div><div class="desk-panel" id="desk-panel-references" role="tabpanel" aria-labelledby="desk-tab-references"></div><div class="desk-panel" id="desk-panel-plan" role="tabpanel" aria-labelledby="desk-tab-plan" hidden>${planPanel(note,plan)}</div><div class="desk-panel" id="desk-panel-tutor" role="tabpanel" aria-labelledby="desk-tab-tutor" hidden><div class="desk-tutor-heading"><h2>Tutor</h2><button class="btn quiet" id="desk-tutor-source">View source passage</button></div><p class="tiny">Ask about the text you are writing. Your editor stays here.</p><div id="desk-tutor-host"></div></div><div class="desk-panel" id="desk-panel-outline" role="tabpanel" aria-labelledby="desk-tab-outline" hidden>${deskOutlineHTML(note,plan)}</div></aside></div><footer class="desk-footer"><div class="desk-save"><p id="paper-save-status" role="status">Saved in Obsidian · ${esc(deskTitle(note.title))}</p><button class="btn quiet" id="paper-save-now">Save now</button><button class="btn secondary" id="paper-mark-complete">Approve this draft</button></div><nav class="desk-next" aria-label="Move through your paper"><button class="btn secondary" id="desk-open-support">Writing support</button><button class="btn" id="desk-next">Next →</button></nav></footer>`:`<section class="desk-project-home"><div class="desk-home-heading"><p class="tiny">YOUR WRITING</p><h1>${esc(deskTitle(note.id===plan.id?plan.title:note.title))}</h1><p>Choose a part, write in your own words, and approve the version you want to export.</p></div><div class="actions"><button class="btn secondary" id="desk-organise">Edit paper outline</button>${['section','subsection'].includes(note.type)?`<a class="btn" href="#section-writing/${encodeURIComponent(plan.id)}?section=${encodeURIComponent(note.id)}">Write this whole section</a>`:''}</div><div id="desk-project-list"></div>${sectionGuidance(note,plan)}<p class="tiny" id="paper-save-status" role="status">Your existing outline and manuscript cards are used here.</p><button id="paper-save-now" hidden>Save now</button></section>`}</div>`;
 }
 function sectionGuidance(note,plan){return deskGuideHTML(note,plan,{editable:false})}
 function planPanel(note,plan){return deskGuideHTML(note,plan)}
 function outlineHTML(plan,note,scope){
  const args=deskArguments(plan,scope),sections=deskSections(plan);
  return `<div class="desk-outline-heading"><h2>Where you are writing</h2><button class="btn quiet" id="desk-outline-close">Close outline</button></div><label class="desk-scope">Show<select id="desk-scope"><option value="all" ${scope==='all'?'selected':''}>All sections</option>${sections.map(s=>`<option value="${esc(s.id)}" ${scope===s.id?'selected':''}>${esc(deskTitle(s.title))}</option>`).join('')}</select></label>${sections.filter(s=>scope==='all'||s.id===scope).map(section=>`<section class="desk-outline-section"><h3>${esc(deskTitle(section.title))}</h3><ol>${args.filter(n=>sectionFor(plan,n.id)===section.id).map(n=>`<li><a href="${paperRoute(plan.id,n.id)}" ${n.id===note.id?'aria-current="page"':''}><span>${esc(deskTitle(n.title))}</span><small>${n.writing_status==='complete'?'✓ Approved':n.fields['Manuscript prose']?.trim()?'Draft':'To write'}</small></a></li>`).join('')}</ol></section>`).join('')}`;
 }
 function help(){modal('A simple writing session',`<ol><li>Use <strong>Paper outline</strong> to expand and read any part. Choose <strong>Open this part for editing</strong> to switch after saving.</li><li><strong>Read previous part</strong> shows its saved text while your draft and references stay visible. <strong>Return to my draft</strong> restores your cursor.</li><li>Keep <strong>References</strong> beside your text. Yellow marks the supporting quotation; the surrounding passage and page numbers stay available.</li><li>Write in your own words. Put the cursor where the reference belongs and choose <strong>Insert citation</strong>.</li><li>Keep the paragraph’s bullet points in <strong>Outline</strong>. Edit or copy them as needed; they stay separate from your manuscript.</li><li>Use <strong>Tutor</strong> when you want feedback. It reviews a snapshot and never moves you to an exercise.</li><li><strong>Approve this draft</strong> when you are happy with it, then choose <strong>Next</strong>.</li><li><strong>Export approved text</strong> previews only approved manuscript paragraphs. Download them in your Springer Nature template, or copy section text into your existing Overleaf document.</li></ol><p>Editing approved prose makes it a draft again. Your earlier versions remain in Compare & recover. Planning notes and quotations are never included in the LaTeX export.</p><p>Use the bibliography from your Overleaf project so citation keys match. Loading a bibliography here does not change the Overleaf project.</p>`)}
 async function exportPreview(c,flush){
  await flush();const plan=await api(`/workspace/papers/${c.paper}`),sections=deskSections(plan),usesLatex=plan.nodes.some(n=>/\\(?:begin|textbf|section|subsection)\b/.test(n.fields?.['Manuscript prose']||''));
  modal('Export approved text',`<p>Preview approved text in your Springer Nature 3.1 template. Download the document and its cited bibliography for Overleaf.</p><div class="desk-export-sections">${sections.map((n,i)=>`<label class="checkbox-row"><input type="checkbox" data-export-section="${esc(n.id)}" checked>${esc(deskTitle(n.title))}</label>`).join('')}</div><details><summary>LaTeX options</summary><label class="field">My writing format<select id="desk-export-mode"><option value="plain" ${usesLatex?'':'selected'}>Plain text with citations and inline maths</option><option value="latex" ${usesLatex?'selected':''}>I write LaTeX commands directly</option></select></label></details><button class="btn" id="desk-export-preview">Preview approved text</button><p id="desk-export-status" role="status"></p><div id="desk-export-result"></div>`);
  $('#desk-export-preview').onclick=async()=>{
   const button=$('#desk-export-preview');button.disabled=true;
   try{
    const selected=[...document.querySelectorAll('[data-export-section]:checked')].map(n=>n.dataset.exportSection);if(!selected.length)throw new Error('Choose at least one section.');
    const data=await api(`/workspace/papers/${c.paper}/latex-preview`,{section_ids:selected,expected_hashes:Object.fromEntries(plan.nodes.map(n=>[n.id,n.hash])),mode:$('#desk-export-mode').value});
    if(data.included.length&&!data.document_tex)throw new Error('Restart Writing Lab to load the updated Springer Nature exporter, then preview again.');
    const warnings=[...(data.warnings||[])];if(data.missing_keys===null)warnings.push('No bibliography is selected yet; citation keys have not been checked.');else if(data.missing_keys?.length)warnings.push('Missing bibliography entries: '+data.missing_keys.join(', '));
    $('#desk-export-status').textContent=`${data.included.length} approved parts included · ${data.skipped.length} parts omitted.`;
    $('#desk-export-result').innerHTML=`${warnings.length?`<div class="alert"><strong>Check before pasting</strong><ul>${warnings.map(w=>`<li>${esc(typeof w==='string'?w:JSON.stringify(w))}</li>`).join('')}</ul></div>`:''}<label class="field">Preview<select id="desk-export-view"><option value="document">Complete Springer Nature document</option><option value="sections">Section text for pasting</option></select></label><label class="field">LaTeX<textarea id="desk-export-text" rows="16" readonly spellcheck="false">${esc(data.document_tex||'')}</textarea></label><div class="actions"><button class="btn" id="desk-download-tex" ${!data.included.length?'disabled':''}>Download main.tex</button>${data.bibtex?' <button class="btn secondary" id="desk-download-bib">Download sn-bibliography.bib</button>':''}<button class="btn quiet" id="desk-copy-tex" ${!data.included.length?'disabled':''}>Copy section text</button></div><details><summary>Included and omitted parts</summary><ul>${data.included.map(n=>`<li>Included: ${esc(deskTitle(n.title))}</li>`).join('')}${data.skipped.map(n=>`<li>Omitted: ${esc(deskTitle(n.title))} — ${esc(({not_approved:'not approved yet',empty:'no manuscript text'})[n.reason]||n.reason||n.status||'not approved')}</li>`).join('')}</ul></details><p class="tiny">The document uses your supplied Springer Nature 3.1 template (sn-jnl, sn-mathphys-num). Upload main.tex and sn-bibliography.bib alongside sn-jnl.cls and sn-mathphys-num.bst; add your authors, affiliations and abstract when ready. Figure files stay separate. To extend an existing manuscript, use Copy section text and merge the cited entries into its bibliography. This subset must not replace a bibliography used by other sections. Overleaf is not changed automatically.</p>`;
    const download=(name,value)=>{const url=URL.createObjectURL(new Blob([value],{type:'text/plain;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000)};
    $('#desk-export-view').onchange=e=>{$('#desk-export-text').value=e.target.value==='document'?(data.document_tex||''):data.tex};
    $('#desk-copy-tex').onclick=async()=>{try{await navigator.clipboard.writeText(data.tex);toast('Approved section text copied.')}catch{$('#desk-export-view').value='sections';$('#desk-export-text').value=data.tex;$('#desk-export-text').focus();$('#desk-export-text').select();toast('Select and copy the section text.')}};
    $('#desk-download-tex').onclick=()=>download(data.document_filename,data.document_tex);
    if($('#desk-download-bib'))$('#desk-download-bib').onclick=()=>download(data.bibliography_filename,data.bibtex);
   }catch(e){$('#desk-export-status').textContent=e.message}finally{if(button.isConnected)button.disabled=false}
  };
 }
 function mount(c,{flush,changed,complete,planning,isActive}){
  const plan=c.plan,note=c.note,writing=note.type==='argument',control=new AbortController();let tutor=null,refs=null,reading=null,guide=null,outline=null,openedTutor=false,tab='references';
  const current=()=>isActive()&&!!$('[data-paper-desk]');
  const key='awl-desk-scope-'+plan.id;let scope=stored(key,'all');if(scope!=='all'&&!deskSections(plan).some(s=>s.id===scope))scope='all';
  if(writing)scope='all'; // Reading the outline never changes the Next sequence.
  const go=async id=>{try{await flush();if(current())location.hash=paperRoute(plan.id,id)}catch(e){toast(e.message)}};
  function bindLinks(root){root.querySelectorAll('a[href^="#papers/"]').forEach(a=>a.onclick=async e=>{e.preventDefault();try{await flush();if(current())location.hash=a.getAttribute('href')}catch(err){toast(err.message)}})}
  function drawOutline(){
   $('#desk-outline').innerHTML=outlineHTML(plan,note,scope);$('#desk-outline-close').onclick=()=>toggleOutline(false);
   $('#desk-scope').onchange=e=>{scope=e.target.value;keep(key,scope);drawOutline();updateStep();if(!writing)home()};bindLinks($('#desk-outline'));
  }
  function toggleOutline(open){$('#desk-outline').hidden=!open;$('#desk-outline-toggle').setAttribute('aria-expanded',String(open));if(open)$('#desk-outline-close').focus();else $('#desk-outline-toggle').focus()}
  function home(){
   let args=deskArguments(plan,scope);if(note.id!==plan.id)args=args.filter(n=>n.id===note.id||sectionFor(plan,n.id)===sectionFor(plan,note.id));
   const resume=stored('awl-desk-last-'+plan.id,null),candidate=args.find(n=>n.id===resume)||args.find(n=>n.writing_status!=='complete')||args[0];
   $('#desk-project-list').innerHTML=`${candidate?`<a class="btn desk-resume" href="${paperRoute(plan.id,candidate.id)}">Resume writing → ${esc(deskTitle(candidate.title))}</a>`:''}<div class="desk-home-sections">${deskSections(plan).map(s=>`<section><h2>${esc(deskTitle(s.title))}</h2><a class="btn secondary" href="#section-writing/${encodeURIComponent(plan.id)}?section=${encodeURIComponent(s.id)}">Write whole section</a><ol>${args.filter(n=>sectionFor(plan,n.id)===s.id).map(n=>`<li><a href="${paperRoute(plan.id,n.id)}">${esc(deskTitle(n.title))}</a><small>${n.writing_status==='complete'?'✓ Approved':n.fields['Manuscript prose']?.trim()?'Draft saved':'To write'}</small></li>`).join('')}</ol></section>`).join('')}</div>`;bindLinks($('#desk-project-list'));
  }
  function updateStep(){if(!writing)return;const args=deskArguments(plan,scope),index=args.findIndex(n=>n.id===note.id);$('#desk-step').textContent=`Part ${index+1} of ${args.length}`;const f=flowNeighbours(plan,note.id);$('#desk-previous').title=f.before?deskTitle(f.before.title):'This is the first part';const next=args[index+1];$('#desk-next').textContent=next?'Next →':'Back to outline';$('#desk-next').title=next?deskTitle(next.title):'This is the end of the selected writing scope';$('#desk-next').onclick=()=>go(next?.id)}
  function showTab(name){
   tab=name;$('#desk-companion').hidden=false;$('#desk-body').classList.remove('desk-support-closed');
   document.querySelectorAll('[data-desk-tab]').forEach(b=>{const on=b.dataset.deskTab===name;b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1});
   for(const n of SUPPORT_TABS)$('#desk-panel-'+n).hidden=n!==name;
   if(name==='tutor'&&!openedTutor){openedTutor=true;tutor.open()}
  }
  guide=mountDeskGuide({host:$('#desk-plan-guide'),note,plan,editor:$('#desk-manuscript'),current,
   onReference:async(e,a,context)=>{
    let target;try{target=new URL(a.href,location.href)}catch{return}
    if(target.origin!==location.origin||!target.hash.startsWith('#papers/'))return;
    const match=target.hash.match(/^#papers\/([^?]+)(?:\?card=([^&]+))?$/);
    if(!match||match[1]!==plan.id||!plan.nodes.some(n=>n.id===match[2]))return;
    e.preventDefault();
    if(context.page!=='opening-sources'){await go(match[2]);return}
    try{
     const sourceNote=match[2]===note.id?{...c.note,fields:{...c.note.fields,...c.dirty}}:await api(`/workspace/papers/${plan.id}/cards/${match[2]}`);
     if(!current()||!context.stillReading()||$('#desk-panel-plan')?.hidden)return;
     modal('Source notes · '+deskTitle(sourceNote.title),`<div class="desk-source-popup paper-markdown">${rich(sourceNote.fields?.['Source mapping']||'No source passage is attached to this part.',sourceNote,plan)}</div><p class="tiny">Read only. Closing returns to the same writing help.</p>`);
     $('#modal')?.addEventListener('close',()=>{if(current()&&a.isConnected)a.focus({preventScroll:true})},{once:true,signal:control.signal});
    }catch(err){if(current()&&context.stillReading())toast(err.message)}
   }});
  if(!writing){$('#desk-outline-toggle').onclick=()=>toggleOutline($('#desk-outline').hidden);drawOutline();}
  $('#desk-planning').onclick=planning;$('#desk-timer').onclick=()=>document.body.classList.toggle('desk-show-timer');
  $('#desk-help').onclick=e=>{e.preventDefault();help()};$('#desk-export').onclick=()=>exportPreview(c,flush).catch(e=>toast(e.message));
  if(writing){
   keep('awl-desk-last-'+plan.id,note.id);const editor=$('#desk-manuscript');
   outline=mountDeskOutline({host:$('#desk-panel-outline'),note,plan,toast,current});
   refs=mountDeskReferences({host:$('#desk-panel-references'),editor,note:c.note,plan,api,esc,toast,modal,citedHost:$('#desk-cited-sources'),current,
    getSourceMapping:()=>c.dirty['Source mapping']??c.note.fields?.['Source mapping']??'',
    saveSourceMapping:async value=>{changed('Source mapping',value);await flush();}});
   $('#desk-tutor-source').onclick=()=>refs.showCurrentSource();
   tutor=mountPaperDeskTutor({host:$('#desk-tutor-host'),editor,paperId:plan.id,cardId:note.id,api,esc,current,flush});
   document.querySelectorAll('[data-desk-tab]').forEach(b=>{b.onclick=()=>showTab(b.dataset.deskTab);b.onkeydown=e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();const next=nextSupportTab(b.dataset.deskTab,e.key);showTab(next);$('#desk-tab-'+next).focus()}}});
   $('#desk-hide-support').onclick=()=>{$('#desk-companion').hidden=true;$('#desk-body').classList.add('desk-support-closed');editor.focus({preventScroll:true})};
   $('#desk-open-support').onclick=()=>showTab(tab);
   const contextKey='awl-desk-reading-'+plan.id;
   reading=mountReadingContext({host:$('#desk-reading-context'),body:$('#desk-body'),editor,plan,noteId:note.id,api,esc,title:deskTitle,current,go,
    getCurrentNote:()=>({...c.note,fields:{...c.note.fields,...c.dirty,'Manuscript prose':editor.value}}),
    onMode:mode=>{keep(contextKey,mode);$('#desk-previous').setAttribute('aria-expanded',String(mode==='previous'));for(const id of ['desk-outline-toggle','desk-context-outline'])$('#'+id).setAttribute('aria-expanded',String(mode==='outline'));}});
   $('#desk-previous').onclick=()=>reading.toggle('previous');
   $('#desk-outline-toggle').onclick=$('#desk-context-outline').onclick=()=>reading.toggle('outline');
   const rememberedContext=stored(contextKey,null);if(['previous','outline'].includes(rememberedContext))reading.open(rememberedContext,{focus:false});
   $('#paper-mark-complete').onclick=async()=>{const button=$('#paper-mark-complete');button.disabled=true;try{await flush();const approved=editor.value;await complete();if(!current())return;if(editor.value!==approved){$('#paper-writing-state').textContent='Draft · changed since approval';toast('The saved version was approved. Your newer edits remain a draft.');return;}$('#paper-writing-state').textContent='✓ Approved for export';$('#paper-writing-state').classList.add('green');toast('This exact draft is approved for export.')}catch(e){toast(e.message)}finally{if(button.isConnected)button.disabled=false}};
   editor.addEventListener('input',()=>{$('#desk-word-count').textContent=words(editor.value)+' words';$('#paper-writing-state').classList.remove('green')},{signal:control.signal});
   updateStep();
   document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#modal')?.open){if(!$('#desk-reading-context').hidden)reading.close();else editor.focus({preventScroll:true})}},{signal:control.signal});
  }else {home();$('#desk-organise').onclick=planning;}
  return {dispose(){control.abort();outline?.dispose();guide?.dispose();reading?.dispose();refs?.dispose();tutor?.dispose()}};
 }
 return {shell,mount};
}
