import {renderPaperMarkdown,paperLinkResolver} from './paper-markdown.js';
export function createPaperContextUI({api,esc,modal,toast}){
 const route=(paper,card)=>'#papers/'+encodeURIComponent(paper)+(card?'?card='+encodeURIComponent(card):'');
 function rich(text,note,plan){return renderPaperMarkdown(text,{resolve:paperLinkResolver(note,plan)});}
 function field(name,text,note,plan){return text?`<details class="paper-context-detail"><summary>${esc(name)}</summary><div class="paper-context-text paper-markdown">${rich(text,note,plan)}</div></details>`:''}
 function guidance(note,plan){
  const f=note.fields,previous=Array.isArray(note.meta.previous_card_ids)?note.meta.previous_card_ids:[];
  const candidates=[...(plan.unplaced||[]),...plan.nodes].filter(n=>previous.includes(n.id));
  return `${f['Main message']?`<div class="paper-main-message"><span class="tag neutral">PLANNING GUIDANCE</span><h3>What this argument should establish</h3><p>${esc(f['Main message'])}</p></div>`:''}
   ${f['Writing task']?`<section class="paper-writing-task"><h3>Your next writing task</h3><p>${esc(f['Writing task'])}</p><p class="tiny">The supplied plan and examples are guidance. Write your own text in Manuscript prose below.</p></section>`:''}
   ${candidates.length?`<details class="paper-reuse-candidates"><summary>Use earlier text · ${candidates.length} mapped ${candidates.length===1?'argument':'arguments'}</summary><p class="tiny">These are earlier writing candidates, not approved replacements for this argument. Read, then choose what still fits.</p>${candidates.map(n=>`<section><h4><a href="${route(plan.id,n.id)}">${esc(n.title)}</a></h4>${n.fields['Manuscript prose']?`<p class="tiny">Your earlier saved prose</p><blockquote class="paper-context-text">${esc(n.fields['Manuscript prose'])}</blockquote>`:'<p class="tiny">No manuscript prose in this card. Its notes remain available.</p>'}<a class="btn quiet" href="${route(plan.id,n.id)}">Read earlier notes & reasoning →</a></section>`).join('')}</details>`:''}
   ${field('Supervisor comments & consequences',f['Supervisor comments and editing consequences'],note,plan)}
   ${field('Role in the argument',f['Role in the argument'],note,plan)}
   ${field('Scope and boundaries',f['Scope and boundaries'],note,plan)}
   ${field('Sources and their limits',f['Source mapping'],note,plan)}`;
 }
 function revision(plan){return plan.fields['Outline revision']?`<div class="paper-revision-bar"><div><span class="tiny">CURRENT WORKING OUTLINE</span><p>${esc(plan.fields['Outline revision'])}</p></div><button class="btn secondary" id="paper-outline-history">Earlier outlines</button></div>${field('Revision guidance & sources',plan.fields['Revision resources'],plan,plan)}`:''}
 async function history(plan){
  try{
   const versions=await api(`/workspace/papers/${plan.id}/outline-versions`);
   modal('Earlier paper outlines',`<p>Read the structure and writing saved before a revision. The current working outline stays active.</p>${versions.map(v=>`<button class="btn secondary" data-outline-version="${esc(v.id)}">${esc(v.label)}</button>`).join('')||'<p>No earlier structural snapshot has been saved.</p>'}`);
   document.querySelectorAll('[data-outline-version]').forEach(b=>b.onclick=async()=>{
    try{
     const version=await api(`/workspace/papers/${plan.id}/outline-versions/${b.dataset.outlineVersion}`);
     const draw=id=>{
      const n=version.nodes.find(n=>n.id===id)||version.outline;
      modal(version.label,`<span class="tag neutral">EARLIER OUTLINE · READ ONLY</span><p>Your current manuscript stays in the working outline.</p><label class="field">Read a saved card<select id="snapshot-card"><option value="">Whole outline</option>${version.nodes.map(n=>`<option value="${esc(n.id)}">${esc(n.type+' · '+n.title)}</option>`).join('')}</select></label><h3>${esc(n.title)}</h3>${Object.entries(n.fields).filter(([,v])=>v).map(([k,v])=>`<h4>${esc(k)}</h4><div class="paper-context-text">${esc(v)}</div>`).join('')}<p><a class="btn secondary" href="${esc(n.uri)}">Open saved card in Obsidian</a></p>`);
      document.querySelector('#snapshot-card').value=id||'';
      document.querySelector('#snapshot-card').onchange=e=>draw(e.target.value);
     };draw('');
    }catch(e){toast(e.message)}
   });
  }catch(e){toast(e.message)}
 }
 function outside(plan,note,cached){
  const candidates=plan.nodes.filter(n=>n.meta.previous_card_ids?.includes(note.id));
  document.querySelector('#main').innerHTML=`<div class="paper-workspace-header"><div><a href="${route(plan.id)}">← Current ${esc(plan.title)} outline</a><h1>${esc(note.title)}</h1><span class="tag neutral">OUTSIDE THE CURRENT OUTLINE · READ ONLY</span></div></div><section class="card"><p>This earlier card is kept as reference. Continue the revised manuscript in the current argument outline.</p>${candidates.map(n=>`<p><a class="btn secondary" href="${route(plan.id,n.id)}">Continue with ${esc(n.title)} →</a></p>`).join('')}${cached?.fields?`<section class="alert"><h3>Your unfinished browser draft is also kept</h3>${Object.entries(cached.fields).map(([k,v])=>`<h4>${esc(k)}</h4><p class="paper-context-text">${esc(v)}</p>`).join('')}</section>`:''}${Object.entries(note.fields).filter(([,v])=>v).map(([k,v])=>`<h3>${esc(k)}</h3><div class="paper-context-text paper-markdown">${rich(v,note,plan)}</div>`).join('')}<a class="btn quiet" href="${esc(note.uri)}">Open earlier card in Obsidian</a></section>`;
 }
 return {guidance,revision,history,outside};
}
