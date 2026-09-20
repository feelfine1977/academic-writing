import {openLiteratureLibrary,matchLibraryCitation} from './paper-literature.js';
import {renderPaperMarkdown,paperLinkResolver} from './paper-markdown.js';

// Citation choices are user metadata. Quotation text always comes from the live card.
export function splitReferenceBlocks(value){
 const lines=String(value||'').replace(/\r\n?/g,'\n').split('\n');
 const sources=[];let preamble=[],part=null,fence=null;
 for(const line of lines){
  const marker=line.match(/^\s*(`{3,}|~{3,})/);
  if(marker){if(!fence)fence=marker[1][0];else if(marker[1][0]===fence)fence=null;}
  const heading=!fence&&!marker&&line.match(/^###\s+(.+?)\s*#*\s*$/);
  if(heading){part={heading:heading[1],lines:[]};sources.push(part);}
  else if(part)part.lines.push(line);else preamble.push(line);
 }
 if(!sources.length&&preamble.join('\n').trim())return {preamble:'',sources:[{heading:'Linked reference notes',markdown:preamble.join('\n').trim()}]};
 return {preamble:preamble.join('\n').trim(),sources:sources.map(({heading,lines})=>({heading,markdown:lines.join('\n').trim()}))};
}
export function sourceReadingPreview(markdown){
 const parts=String(markdown||'').split(/\n{2,}/),quotes=[],pages=[],context=[],other=[];
 for(const part of parts){
  if(/^>/.test(part.trim()))quotes.push(part);
  else if(/^\*\*(?:Printed page|PDF page|Page number|Location)[:*]/i.test(part.trim()))pages.push(part);
  else if(/^\*\*Context\b/i.test(part.trim()))context.push(part);
  else other.push(part);
 }
 if(!quotes.length)return {primary:markdown,other:''};
 return {primary:[...quotes,...pages,...context].join('\n\n'),other:other.join('\n\n')};
}
export function normaliseReferenceTitle(value){
 return String(value||'').replace(/\\(?:textit|textbf|emph|mathrm|textrm)\s*\{([^{}]*)\}/g,'$1')
  .replace(/\\(?:['"`^~=.]|[uvHckbd]\s*)\{?([A-Za-z])\}?/g,'$1')
  .normalize('NFKD').replace(/\p{M}/gu,'').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();
}
export function suggestBibliographyEntry(source,entries){
 const explicit=source.markdown.match(/^\*\*Citation key:\*\*\s*`([^`]+)`\s*$/m);
 if(explicit)return entries.find(entry=>entry.key===explicit[1])||null;
 const heading=' '+normaliseReferenceTitle(source.heading)+' ';
 const whole=' '+normaliseReferenceTitle(source.heading+' '+source.markdown)+' ';
 const match=text=>entries.filter(entry=>{const title=normaliseReferenceTitle(entry.title);return title.length>=12&&text.includes(' '+title+' ')});
 const found=match(heading);if(found.length)return found.length===1?found[0]:null;
 const expanded=match(whole);return expanded.length===1?expanded[0]:null;
}
export function validCitationKey(key){return typeof key==='string'&&/^[\p{L}\p{N}_][\p{L}\p{N}_.:+/\-]*$/u.test(key);}
export function validateBibliography(value){
 if(!value||typeof value!=='object'||!Array.isArray(value.entries)||typeof value.bibtex!=='string'||!(value.filename==null||typeof value.filename==='string'))throw new Error('The bibliography response could not be read. Your previous citation choices are kept.');
 const keys=new Set();
 for(const entry of value.entries){
  if(!entry||!validCitationKey(entry.key)||keys.has(entry.key)||['title','author','year','doi'].some(field=>entry[field]!=null&&!['string','number'].includes(typeof entry[field])))throw new Error('The bibliography contains an invalid or duplicate entry. Your previous citation choices are kept.');
  keys.add(entry.key);
 }
 return {bibtex:value.bibtex,filename:value.filename||'',hash:typeof value.hash==='string'?value.hash:null,basis:typeof value.basis==='string'?value.basis:'none',uri:typeof value.uri==='string'&&value.uri.startsWith('obsidian://open?')?value.uri:null,entries:value.entries.map(entry=>({...entry,title:String(entry.title||''),author:String(entry.author||''),year:String(entry.year||'')}))};
}
export function insertCitationAtCaret(value,key,selectionEnd){
 if(!validCitationKey(key))throw new Error('Choose a valid entry from your bibliography first.');
 const text=String(value||'');let offset=Number.isFinite(selectionEnd)?Math.trunc(selectionEnd):text.length;
 offset=Math.max(0,Math.min(text.length,offset));
 // Textarea selections use UTF-16 offsets. A stale selection must not split an emoji.
 if(offset>0&&offset<text.length&&/[\uD800-\uDBFF]/.test(text[offset-1])&&/[\uDC00-\uDFFF]/.test(text[offset]))offset++;
 const before=text.slice(0,offset),after=text.slice(offset);
 const left=before&&!/[\s([{]$/.test(before)?' ':'';
 const right=after&&!/^[\s.,;:!?)\]}]/.test(after)?' ':'';
 const citation='\\cite{'+key+'}',insertion=left+citation+right;
 return {text:before+insertion+after,offset,insertion,caret:offset+left.length+citation.length};
}

export function referencePassageBlock({entry,passage,printedPage,pdfPage,context,overview='',limits='',supports=''}){
 if(!entry||!validCitationKey(entry.key))throw new Error('Choose the publication from your bibliography.');
 const clean=value=>String(value||'').replace(/\r\n?/g,'\n').trim();
 const line=value=>clean(value).replace(/\n/g,' ');
 const paragraph=value=>clean(value).replace(/^(\s*)(#{1,6})(?=\s)/gm,'$1\\$2');
 passage=clean(passage);context=paragraph(context);
 printedPage=line(printedPage);pdfPage=line(pdfPage);
 if(!passage)throw new Error('Paste the quotation with enough surrounding text to understand it.');
 if(!printedPage&&!pdfPage)throw new Error('Add a printed page or PDF page number so you can find the passage again.');
 if(!context)throw new Error('Add a short description of what the author is discussing here.');
 const heading=line(entry.title||entry.key)+(entry.year?' ('+line(entry.year)+')':'')+' · '+entry.key;
 const parts=['### '+heading,'**Citation key:** `'+entry.key+'`',passage.split('\n').map(l=>'> '+l).join('\n'),
  [printedPage?'**Printed page:** '+printedPage:null,pdfPage?'**PDF page:** '+pdfPage:null].filter(Boolean).join('; '),
  '**Context (your note):** '+context];
 if(clean(overview))parts.push('**Paper in brief:** '+paragraph(overview));
 if(clean(supports))parts.push('**Supports:** '+paragraph(supports));
 if(clean(limits))parts.push('**Use with care:** '+paragraph(limits));
 return {heading,markdown:parts.join('\n\n')};
}
export function appendReferencePassage(existing,block){
 const original=String(existing||'');
 // A retry after a failed save must not append the same passage twice.
 const padded='\n\n'+original,needle='\n\n'+block,index=padded.indexOf(needle),end=index+needle.length;
 if(index>=0&&(end===padded.length||padded[end]==='\n'))return original;
 return original+(original?(original.endsWith('\n\n')?'':original.endsWith('\n')?'\n':'\n\n'):'')+block;
}

export function mountDeskReferences({host,editor,note,plan,api,esc,toast,modal,citedHost,getSourceMapping,saveSourceMapping,current=()=>true}){
 const controller=new AbortController(),signal=controller.signal;
 const paper=encodeURIComponent(plan.id),storageKey='awl-desk-citation-choices-'+plan.id;
 let source=splitReferenceBlocks(getSourceMapping?.()??note.fields?.['Source mapping']);
 const resolve=paperLinkResolver(note,plan),rich=text=>renderPaperMarkdown(text,{resolve});
 let live=true,generation=0,entries=[],bibliography=null,caret=editor.selectionEnd??editor.value.length,choices={};
 try{const saved=JSON.parse(localStorage.getItem(storageKey)||'{}');if(saved&&typeof saved==='object'&&!Array.isArray(saved))choices=Object.fromEntries(Object.entries(saved).filter(([,v])=>validCitationKey(v)));}catch{}
 const remember=()=>{caret=editor.selectionEnd??editor.value.length;};
 for(const name of ['select','keyup','mouseup','pointerup','input','blur'])editor.addEventListener(name,remember,{signal});
 const isLive=()=>live&&current()&&host.isConnected;
 const shorten=(value,max=85)=>value.length>max?value.slice(0,max-1).trimEnd()+'…':value;
 const reading=s=>{const preview=sourceReadingPreview(s.markdown);return `<div class="paper-markdown desk-reference-text">${rich(preview.primary)}</div>${preview.other?`<details class="desk-source-background"><summary>Paper overview and interpretation</summary><div class="paper-markdown">${rich('### '+s.heading+'\n\n'+preview.other)}</div></details>`:''}`};
 host.innerHTML=`<div class="desk-reference-intro"><p>Read the passage and its context beside your writing. Insert only the citation into your manuscript.</p></div><details class="desk-cite-any"><summary>Cite another source</summary><div data-cite="catalogue"></div></details><details class="desk-reference-bibliography"><summary>Bibliography for citations <span data-bib-count></span></summary><p>Keep one bibliography in Obsidian. Add BibTeX copied from Google Scholar, or load your existing file. The same keys work in Overleaf.</p><div data-bib-location></div><details><summary>Add a BibTeX entry</summary><label class="field">Paste BibTeX<textarea data-bib-paste rows="6" spellcheck="false" placeholder="@article{key, title={...}, ...}"></textarea></label><button type="button" class="btn secondary" data-bib-add>Add to Obsidian bibliography</button></details><label class="field">Bibliography file<input type="file" accept=".bib,text/plain" data-bib-file></label><div class="actions"><button type="button" class="btn secondary" data-bib-load>Add entries from file</button><button type="button" class="btn quiet" data-bib-reload>Reload</button><button type="button" class="btn quiet" data-bib-create>Keep bibliography in Obsidian</button><button type="button" class="btn quiet" data-bib-download>Download .bib</button></div><p class="tiny" data-bib-status role="status"></p></details>${source.preamble?`<details class="desk-reading-key"><summary>How to read these source notes</summary><div class="paper-markdown desk-reference-preamble">${rich(source.preamble)}</div></details>`:''}<div class="desk-reference-sources">${source.sources.map((s,i)=>`<details class="desk-reference-source" data-source="${i}" ${i===0?'open':''}><summary title="${esc(s.heading)}">${esc(shorten(s.heading))}</summary><div class="desk-reference-cite" data-cite="${i}"></div>${reading(s)}</details>`).join('')||'<p class="desk-reference-empty">No reference passages are linked to this argument yet. Its saved planning notes remain available in Plan.</p>'}</div>`;
 const $=selector=>host.querySelector(selector);
 if(saveSourceMapping)$('.desk-reference-intro').insertAdjacentHTML('afterend',`<details class="desk-add-passage"><summary>Add quotation and context</summary><form data-passage-form><fieldset><label class="field">Publication<select data-passage-entry required aria-label="Publication for quotation"><option value="">Loading bibliography…</option></select></label><label class="field">Passage with surrounding sentences<textarea data-passage-text rows="5" required placeholder="Paste the original wording. Put == around the supporting words to highlight them yellow."></textarea></label><p class="tiny">Keep the author's wording. Use ==supporting words== for yellow highlighting; the rest stays black.</p><div class="desk-passage-pages"><label class="field">Printed page<input data-passage-printed placeholder="e.g. 1261"></label><label class="field">PDF page<input data-passage-pdf placeholder="e.g. 9"></label></div><label class="field">Context: what is the author discussing?<textarea data-passage-context rows="3" required placeholder="Describe the section, example or argument around this passage."></textarea></label><details><summary>Paper overview and limits (optional)</summary><label class="field">Overall message of the paper<textarea data-passage-overview rows="3"></textarea></label><label class="field">What this passage does not establish<textarea data-passage-limits rows="2"></textarea></label></details><button class="btn secondary" type="submit">Save quotation to this paragraph</button></fieldset><p data-passage-status class="tiny" role="status"></p></form></details>`);
 if(saveSourceMapping){
  $('.desk-reference-intro').insertAdjacentHTML('beforeend','<button type="button" class="btn secondary" data-literature-open>Find in literature library</button>');
  $('[data-literature-open]').addEventListener('click',()=>openLiteratureLibrary({api,modal,esc,current:isLive,onAttach:async (publication,quotation)=>{
   if(!isLive())throw new Error('Return to the paragraph before adding its reference.');
   // Reload before matching/merging to preserve bibliography edits from other views.
   accept(await api(`/workspace/papers/${paper}/bibliography`));
   if(!isLive())throw new Error('The paragraph changed. Reopen its reference panel.');
   let entry=matchLibraryCitation(publication,entries);
   if(!entry){
    if(publication.conflicting_keys?.length)throw new Error('This exported citation key identifies more than one source. Resolve it in Obsidian before adding the entry.');
    if(!publication.bibtex)throw new Error('Add a verified BibTeX entry in the bibliography first.');
    accept(await api(`/workspace/papers/${paper}/bibliography/merge`,{bibtex:publication.bibtex,base_hash:bibliography?.hash??null}));
    entry=matchLibraryCitation(publication,entries);
    if(!entry)throw new Error('The publication could not be matched uniquely. Choose its bibliography entry manually.');
   }
   if(!isLive())throw new Error('The bibliography was saved. Return to the paragraph to attach the quotation.');
   const block=referencePassageBlock({entry,...quotation,overview:publication.overview||''});
   const linked=block.markdown+(publication.uri?'\n\n[Full literature card]('+publication.uri+')':'');
   const mapping=appendReferencePassage(getSourceMapping?.()??note.fields?.['Source mapping'],linked);
   await saveSourceMapping(mapping);
   if(isLive()){source=splitReferenceBlocks(mapping);storeChoice(block.heading,entry.key);drawPassages();toast('Quotation and context saved beside your paragraph.');}
  }}),{signal});
 }
 const status=(message,error=false)=>{if(!isLive())return;const el=$('[data-bib-status]');el.textContent=message;el.classList.toggle('error',error);};
 function drawPassageChoices(){
  const select=$('[data-passage-entry]');if(!select)return;
  const selected=select.value;
  select.innerHTML=`<option value="">${entries.length?'Choose the publication':'Add a bibliography entry below first'}</option>${entries.map(e=>`<option value="${esc(e.key)}">${esc(e.title||e.key)}${e.year?' ('+esc(e.year)+')':''} · ${esc(e.key)}</option>`).join('')}`;
  select.value=entries.some(e=>e.key===selected)?selected:entries.length===1?entries[0].key:'';
 }
 function drawPassages(){
  $('.desk-reference-sources').innerHTML=source.sources.map((s,i)=>`<details class="desk-reference-source" data-source="${i}" ${i===source.sources.length-1?'open':''}><summary title="${esc(s.heading)}">${esc(shorten(s.heading))}</summary><div class="desk-reference-cite" data-cite="${i}"></div>${reading(s)}</details>`).join('');
  drawCitations();showCited();
 }
 $('[data-passage-form]')?.addEventListener('submit',async event=>{
  event.preventDefault();const form=event.currentTarget,fieldset=form.querySelector('fieldset'),message=$('[data-passage-status]');
  const value=name=>$('[data-passage-'+name+']').value;
  try{
   const entry=entries.find(e=>e.key===value('entry'));
   const block=referencePassageBlock({entry,passage:value('text'),printedPage:value('printed'),pdfPage:value('pdf'),context:value('context'),overview:value('overview'),limits:value('limits')});
   fieldset.disabled=true;message.textContent='Saving quotation and context to Obsidian…';message.classList.remove('error');
   const mapping=appendReferencePassage(getSourceMapping?.()??note.fields?.['Source mapping'],block.markdown);
   await saveSourceMapping(mapping);
   if(!isLive())return;
   source=splitReferenceBlocks(mapping);storeChoice(block.heading,entry.key);drawPassages();
   form.reset();drawPassageChoices();message.textContent='Quotation and context saved in Obsidian.';
   $('.desk-add-passage').open=false;
   $('.desk-reference-bibliography').open=false;$('.desk-cite-any').open=false;
   $('.desk-reference-sources [data-source]:last-child summary')?.focus({preventScroll:true});
   toast('Quotation saved beside your paragraph. Your manuscript text is unchanged.');
  }catch(error){if(isLive()){message.textContent=error.message;message.classList.add('error');}}
  finally{if(fieldset.isConnected)fieldset.disabled=false;}
 },{signal});
 function storeChoice(heading,key){
  if(key)choices[heading]=key;else delete choices[heading];
  try{localStorage.setItem(storageKey,JSON.stringify(choices));}catch{toast('This citation choice works for this session, but browser storage could not retain it.');}
 }
 function showSource(sources,key=''){
  if(!modal)return;
  const entry=entries.find(e=>e.key===key);
  modal('Source passage and context', `<div class="desk-source-popup">${key?`<p class="tiny">Citation key: <code>${esc(key)}</code></p>`:''}${sources.length?sources.map(s=>`<article class="paper-markdown">${rich('### '+s.heading+'\n\n'+s.markdown)}</article>`).join(''):`<h3>${esc(entry?.title||key)}</h3><p>No quotation is linked to this citation in the current argument. Open its literature card or add a checked passage before treating it as support for this claim.</p>`}<p class="tiny">Quotation and context come from your saved source notes. The citation entry identifies the publication; it does not itself verify the claim.</p></div>`);
  editor.ownerDocument.querySelector('#modal')?.addEventListener('close',()=>{if(isLive())editor.focus({preventScroll:true})},{once:true,signal});
 }
 function showCited(){
  if(!citedHost)return;
  const keys=[...new Set([...editor.value.matchAll(/\\(?:citep|citet|cite)\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}/g)].flatMap(m=>m[1].split(',').map(k=>k.trim())))];
  citedHost.hidden=!keys.length;
  citedHost.innerHTML=`<details><summary>Sources cited in this text (${keys.length})</summary><div class="desk-cited-buttons">${keys.map(k=>`<button type="button" class="btn quiet" data-cited-key="${esc(k)}" title="View quotation and context">${esc(k)}</button>`).join('')}</div></details>`;
  citedHost.querySelectorAll('[data-cited-key]').forEach(b=>b.onclick=()=>{const key=b.dataset.citedKey;showSource(source.sources.filter(s=>choices[s.heading]===key||(!choices[s.heading]&&suggestBibliographyEntry(s,entries)?.key===key)),key)});
 }
 editor.addEventListener('input',showCited,{signal});
 function drawCitations(){
  if(!isLive())return;
  for(const [i,s] of [...source.sources.entries(),['catalogue',{heading:'Other bibliography entry',markdown:'',catalogue:true}]]){
   const slot=$(`[data-cite="${i}"]`),existing=entries.find(entry=>entry.key===choices[s.heading]);
   const suggested=existing?null:suggestBibliographyEntry(s,entries),selected=existing||suggested;
   slot.innerHTML=`<details class="desk-citation-picker" ${selected?'':'open'}><summary>${selected?'Citation: '+esc(selected.key):'Choose citation source'}</summary><label class="desk-reference-choice">Citation source<select aria-label="Bibliography entry for ${esc(s.heading)}"><option value="">${entries.length?'Choose bibliography entry':'Load a bibliography first'}</option>${entries.map(entry=>`<option value="${esc(entry.key)}" ${entry.key===selected?.key?'selected':''}>${esc(entry.key+' · '+(entry.title||entry.author||'Untitled entry')+(entry.year?' ('+entry.year+')':''))}</option>`).join('')}</select></label></details><button type="button" class="btn secondary" data-insert-citation ${selected?'':'disabled'}>Insert citation</button><button type="button" class="btn quiet" data-view-source>View source</button><p class="tiny" data-cite-status role="status">${existing?'Uses your chosen bibliography entry.':suggested?'Title match; check the source before citing.':entries.length?'Select the matching source from your bibliography.':'Load your Overleaf .bib file above before inserting a citation.'}</p>`;
   slot.querySelector('[data-view-source]').addEventListener('click',()=>{const key=slot.querySelector('select').value;showSource(s.catalogue?source.sources.filter(item=>choices[item.heading]===key||(!choices[item.heading]&&suggestBibliographyEntry(item,entries)?.key===key)):[s],key)},{signal});
   const select=slot.querySelector('select'),button=slot.querySelector('[data-insert-citation]'),message=slot.querySelector('[data-cite-status]');
   select.addEventListener('change',()=>{const chosen=entries.find(entry=>entry.key===select.value);storeChoice(s.heading,chosen?.key||'');button.disabled=!chosen;slot.querySelector('.desk-citation-picker summary').textContent=chosen?'Citation: '+chosen.key:'Choose citation source';message.textContent=chosen?'Uses your chosen bibliography entry.':'Choose the source you want to cite.';},{signal});
   button.addEventListener('click',()=>{
    const entry=entries.find(entry=>entry.key===select.value);
    if(!entry){message.textContent='Choose an entry from the loaded bibliography first.';return;}
    try{
     const result=insertCitationAtCaret(editor.value,entry.key,caret);
     editor.setRangeText(result.insertion,result.offset,result.offset,'end');
     editor.setSelectionRange(result.caret,result.caret);caret=result.caret;
     storeChoice(s.heading,entry.key);
     const InputEvent=editor.ownerDocument.defaultView.Event;
     editor.dispatchEvent(new InputEvent('input',{bubbles:true}));editor.focus({preventScroll:true});
     message.textContent='Citation inserted. Your selected words and source passage are unchanged.';
    }catch(error){message.textContent=error.message;}
   },{signal});
  }
 }
 function accept(value){
  const checked=validateBibliography(value);bibliography=checked;entries=checked.entries;
  // Retain a user mapping only while its exact key is in the loaded bibliography.
  const keys=new Set(entries.map(entry=>entry.key));
  const filtered=Object.fromEntries(Object.entries(choices).filter(([,key])=>keys.has(key)));
  if(JSON.stringify(filtered)!==JSON.stringify(choices)){choices=filtered;try{localStorage.setItem(storageKey,JSON.stringify(choices));}catch{}}
  const link=$('[data-bib-location]');link.innerHTML=checked.uri?`<p class="tiny"><a href="${esc(checked.uri)}">Open bibliography in Obsidian</a></p>`:'';
  $('[data-bib-create]').hidden=checked.basis==='shared';
  const count=entries.length+' '+(entries.length===1?'entry':'entries');
  $('[data-bib-count]').textContent=entries.length?'· '+count:'';
  drawCitations();showCited();drawPassageChoices();
  status(entries.length?`${checked.filename||'Bibliography'} · ${count} available.`:'No bibliography loaded yet. Your quotation notes are ready to read.');
 }
 async function reloadBibliography(){
  const own=++generation;status('Checking the bibliography…');
  try{const value=await api(`/workspace/papers/${paper}/bibliography`);if(isLive()&&own===generation)accept(value);}
  catch(error){if(isLive()&&own===generation)status(error.message,true);}
 }
 $('[data-bib-reload]').addEventListener('click',reloadBibliography,{signal});
 $('[data-bib-load]').addEventListener('click',async()=>{
  const file=$('[data-bib-file]').files[0];if(!file){status('Choose a .bib file to add its entries.',true);return;}
  if(!/\.bib$/i.test(file.name)){status('Choose a .bib bibliography file.',true);return;}
  const own=++generation,button=$('[data-bib-load]');button.disabled=true;status('Loading the bibliography…');
  try{const bibtex=await file.text();if(!isLive()||own!==generation)return;const result=await api(`/workspace/papers/${paper}/bibliography/merge`,{bibtex,base_hash:bibliography?.hash??null});if(isLive()&&own===generation){accept(result);$('[data-bib-file]').value='';}}
  catch(error){if(isLive()&&own===generation)status(error.message,true);}
  finally{if(isLive())button.disabled=false;}
 },{signal});
 async function mergeBib(bibtex){
  status('Saving bibliography in Obsidian…');
  try{const value=await api(`/workspace/papers/${paper}/bibliography/merge`,{bibtex,base_hash:bibliography?.hash??null});if(isLive()){accept(value);$('[data-bib-paste]').value='';toast('BibTeX saved in Obsidian. Its citation keys are ready to insert.');}}
  catch(error){status(error.message,true);}
 }
 $('[data-bib-add]').addEventListener('click',()=>{const text=$('[data-bib-paste]').value.trim();if(!text){status('Paste the BibTeX entry you want to add.',true);return;}mergeBib(text);},{signal});
 $('[data-bib-create]').addEventListener('click',()=>mergeBib(''),{signal});
 $('[data-bib-download]').addEventListener('click',()=>{if(!bibliography?.bibtex){status('Add a bibliography entry first.',true);return;}const url=URL.createObjectURL(new Blob([bibliography.bibtex],{type:'text/plain;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=bibliography.filename||'references.bib';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);},{signal});
 drawCitations();showCited();reloadBibliography();
 return {dispose(){live=false;generation++;controller.abort();},reloadBibliography,showCurrentSource(){const open=host.querySelector('[data-source][open]');showSource(open?[source.sources[Number(open.dataset.source)]]:source.sources.slice(0,1))}};
}
