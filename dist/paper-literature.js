import {renderPaperMarkdown,safeReadingURL} from './paper-markdown.js';
const clean=value=>String(value||'').toLocaleLowerCase().normalize('NFKD').replace(/[^\p{L}\p{N}]/gu,'');
const doi=value=>String(value||'').toLowerCase().replace(/^https?:\/\/(dx\.)?doi\.org\//,'').trim();
// A citation-key match by itself is insufficient: exported libraries can reuse keys.
export function matchLibraryCitation(source,entries=[]){
 const same=entries.filter(e=>(source.doi&&doi(e.doi)===doi(source.doi)) || (clean(e.title)===clean(source.title)&&String(e.year||'')===String(source.year||'')&&clean(source.title)));
 if(same.length===1)return same[0];
 const keyMatch=same.filter(e=>[source.key,...(source.keys||[])].includes(e.key));
 return keyMatch.length===1?keyMatch[0]:null;
}
export function openLiteratureLibrary({api,modal,esc,onAttach,current=()=>true}){
 modal('Literature library','<div class="desk-library" data-literature-library></div>');
 const host=document.querySelector('[data-literature-library]'),dialog=host.closest('dialog');
 let generation=0,closed=false,search={q:'',topic:'',status:'',scope:'notes'},last=null;
 const live=()=>!closed&&host.isConnected&&current();
 dialog?.addEventListener('close',()=>{closed=true;generation++},{once:true});
 const statusLabel={"passages-checked":"Selected passages checked","reading-guide":"Book reading guide","earlier-notes":"Earlier notes · check before citing","catalogued":"Bibliographic record only"};
 const rich=value=>renderPaperMarkdown(value,{resolve:safeReadingURL});
 function searchView(result=last){
  if(!live())return;
  const topics=result?.topics||[];
  host.innerHTML=`<p>Find a source, read the passage in context, then add it beside your paragraph.</p><form data-library-search><label class="field">Search title, author, topic or citation key<input name="q" type="search" value="${esc(search.q)}" placeholder="e.g. van der Aalst, BPM, business goals" autofocus></label><div class="desk-library-filters"><label>Browse<select name="scope"><option value="notes">Source cards</option><option value="all">Full exported catalogue</option></select></label><label>Topic<select name="topic"><option value="">All topics</option>${topics.map(t=>`<option value="${esc(t)}">${esc(t.replaceAll('-',' '))}</option>`).join('')}</select></label><label>Reading status<select name="status"><option value="">All statuses</option><option value="passages-checked">Checked passages</option><option value="earlier-notes">Earlier notes</option><option value="catalogued">Catalogue only</option></select></label></div><button class="btn secondary">Search library</button></form><p data-library-status role="status" class="tiny">${result?`${result.total} matching sources`:'Loading sources…'}</p><div data-library-results>${result?.entries.map(e=>`<button class="desk-library-result" data-source-id="${esc(e.id)}"><strong>${esc(e.title||e.key||'Untitled source')}</strong><span>${esc(e.author||'Author not recorded')} · ${esc(e.year||'Year not recorded')}</span><small>${esc(statusLabel[e.status]||e.status||'Not checked')}${e.quote_count?' · '+e.quote_count+' quotations':''}</small></button>`).join('')||''}</div>${result?`<div class="actions">${result.offset?'<button class="btn quiet" data-library-prev>← Previous results</button>':''}${result.next_offset!=null?'<button class="btn quiet" data-library-next>More sources →</button>':''}</div>`:''}${result?.warnings?.length?`<details><summary>Library notes need attention (${result.warnings.length})</summary><p>${result.warnings.map(esc).join('<br>')}</p></details>`:''}`;
  const form=host.querySelector('form');for(const name of ['scope','topic','status'])form.elements[name].value=search[name];
  form.addEventListener('submit',event=>{event.preventDefault();for(const name of ['q','scope','topic','status'])search[name]=form.elements[name].value;load(0)});
  for(const name of ['scope','topic','status'])form.elements[name].addEventListener('change',()=>form.requestSubmit());
  host.querySelectorAll('[data-source-id]').forEach(button=>button.addEventListener('click',()=>detail(button.dataset.sourceId)));
  host.querySelector('[data-library-next]')?.addEventListener('click',()=>load(result.next_offset));
  host.querySelector('[data-library-prev]')?.addEventListener('click',()=>load(Math.max(0,result.offset-40)));
 }
 async function load(offset){
  const own=++generation;host.querySelector('[data-library-status]').textContent='Searching…';
  try{const value=await api('/workspace/literature?'+new URLSearchParams({...search,offset:String(offset)}));if(!live()||own!==generation)return;last=value;searchView(value)}
  catch(error){if(live()&&own===generation)host.querySelector('[data-library-status]').textContent=error.message+' If you just updated the app, reopen it to load the library service.'}
 }
 async function detail(id){
  const own=++generation;
  try{
   const s=await api('/workspace/literature/'+encodeURIComponent(id));if(!live()||own!==generation)return;
   host.innerHTML=`<button class="btn quiet" data-library-back>← Search results</button><h3 tabindex="-1">${esc(s.title)}</h3><p class="tiny">${esc(s.author||'')} · ${esc(s.year||'')} · ${esc(statusLabel[s.status]||s.status)}</p><div class="paper-markdown">${rich(s.overview||'No overview has been written yet.')}</div>${safeReadingURL(s.uri)?`<p><a href="${esc(s.uri)}">Open source card and PDF links in Obsidian ↗</a></p>`:''}${s.bibtex?`<details><summary>BibTeX reference</summary><pre><code>${esc(s.bibtex)}</code></pre><p class="tiny">Use the key already present in your paper for the same source. Check exported metadata before publication.</p></details>`:''}${s.guide?`<details><summary>Method, findings and use for WISE</summary><div class="paper-markdown">${rich(s.guide)}</div></details>`:''}${s.reading?`<details><summary>Reading guide and citation details</summary><div class="paper-markdown">${rich(s.reading)}</div></details>`:''}${s.related?.length?`<div class="desk-library-chapters"><h4>Checked chapters</h4>${s.related.map(e=>`<button class="btn quiet" data-related-id="${esc(e.id)}">${esc(e.title)}</button>`).join('')}</div>`:''}${s.quotes?.length?`<label class="field">Choose a passage<select data-library-quote>${s.quotes.map((q,i)=>`<option value="${i}">${esc(q.title)}</option>`).join('')}</select></label><div data-library-passage></div><button class="btn secondary" data-library-attach>Add quotation to this paragraph</button><p class="tiny">This adds reference notes and, if needed, the matching bibliography entry. Your manuscript text stays as you wrote it.</p>`:'<p>No checked quotation is available in this entry. Open the source and record a passage before using it as evidence for a claim.</p>'}<p data-library-status class="tiny" role="status"></p>`;
   host.querySelector('[data-library-back]').addEventListener('click',()=>{generation++;searchView(last)});
   host.querySelectorAll('[data-related-id]').forEach(b=>b.addEventListener('click',()=>detail(b.dataset.relatedId)));
   const choice=host.querySelector('[data-library-quote]');
   const draw=()=>{const q=s.quotes[Number(choice.value)];host.querySelector('[data-library-passage]').innerHTML=`<div class="paper-markdown">${rich('**Context:** '+q.context+'\n\n'+q.passage.split('\n').map(x=>'> '+x).join('\n')+'\n\n**Printed page:** '+q.printedPage+'; **PDF page:** '+q.pdfPage+'\n\n**Supports:** '+q.supports+'\n\n**Use with care:** '+q.limits)}</div>`};
   if(choice){choice.addEventListener('change',draw);draw();}
   host.querySelector('[data-library-attach]')?.addEventListener('click',async event=>{
    const button=event.currentTarget,message=host.querySelector('[data-library-status]');button.disabled=true;message.textContent='Saving the reference notes…';
    try{await onAttach(s,s.quotes[Number(choice.value)]);if(!live())return;message.textContent='Saved beside your paragraph. Close this window to continue writing.';button.textContent='Quotation added';}
    catch(error){if(live()){message.textContent=error.message;button.disabled=false;}}
   });
   host.querySelector('h3').focus({preventScroll:true});
  }catch(error){if(live()&&own===generation)host.querySelector('[data-library-status]').textContent=error.message;}
 }
 searchView();load(0);
}
