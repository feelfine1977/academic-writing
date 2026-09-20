import {renderPaperMarkdown,paperLinkResolver} from './paper-markdown.js';

export const OUTLINE_FIELD='Writing outline';
export const SUPPORT_TABS=['references','plan','tutor','outline'];
export function nextSupportTab(name,key){
 const step=key==='ArrowRight'?1:key==='ArrowLeft'?-1:0;
 return SUPPORT_TABS[(SUPPORT_TABS.indexOf(name)+step+SUPPORT_TABS.length)%SUPPORT_TABS.length];
}
const escapeHTML=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

// A reading view for the outline's small LaTeX subset; never execute TeX or
// transform the saved note. Unrecognised syntax remains visible in the source.
export function outlineMarkdown(value){
 let number=0;
 return String(value||'').split('\n').map(line=>{
  if(/^\s*%/.test(line))return '';
  if(/^\s*\\begin\{(?:enumerate|itemize)\}\s*$/.test(line)){number=0;return '';}
  if(/^\s*\\end\{(?:enumerate|itemize)\}\s*$/.test(line))return '';
  return line.replace(/^\s*\\textbf\{([^{}]*)\}\s*$/,'### $1')
   .replace(/^\s*\\item\s+/,()=>`${++number}. `)
   .replace(/\\cite(?:p|t)?(?:\[[^\]]*\])*\{([^{}]*)\}/g,(_,keys)=>'`['+keys+']`')
   .replace(/\\textbf\{([^{}]*)\}/g,'**$1**')
   .replace(/\\textit\{([^{}]*)\}/g,'*$1*')
   .replace(/\\([&%_])/g,'$1');
 }).join('\n');
}
function preview(value,note,plan){
 return value.trim()?renderPaperMarkdown(outlineMarkdown(value),{resolve:paperLinkResolver(note,plan)}):'<p class="tiny">No outline added yet. Open Edit outline to add your points.</p>';
}
export function deskOutlineHTML(note,plan){
 const value=note.fields?.[OUTLINE_FIELD]||'';
 return `<h2>Outline for this part</h2><p class="tiny">Use these points while writing your own sentences. This note stays separate from the exported manuscript.</p><div class="paper-markdown desk-outline-note" id="desk-outline-note-preview">${preview(value,note,plan)}</div><details class="desk-outline-edit"><summary>Edit outline / LaTeX</summary><label class="field">Writing outline<textarea id="desk-outline-note-editor" data-paper-field="${OUTLINE_FIELD}" rows="12" spellcheck="false" placeholder="Add bullet points or paste a LaTeX list…">${escapeHTML(value)}</textarea></label><p class="tiny">Markdown and LaTeX lists are supported. Changes save to this card in Obsidian.</p></details><div class="actions"><button class="btn secondary" id="desk-outline-copy" ${value.trim()?'':'disabled'}>Copy outline</button><a class="btn quiet" href="${escapeHTML(note.uri)}">Open note in Obsidian</a></div>`;
}
export function mountDeskOutline({host,note,plan,toast,current}){
 const control=new AbortController(),editor=host.querySelector('#desk-outline-note-editor'),copy=host.querySelector('#desk-outline-copy');
 const update=()=>{host.querySelector('#desk-outline-note-preview').innerHTML=preview(editor.value,note,plan);copy.disabled=!editor.value.trim();};
 update(); // Use recovered editor content when there was an unfinished note.
 editor.addEventListener('input',update,{signal:control.signal});
 copy.addEventListener('click',async()=>{
  try{await navigator.clipboard.writeText(editor.value);if(current())toast('Outline copied.');}
  catch{if(current()){host.querySelector('.desk-outline-edit').open=true;editor.focus();editor.select();toast('Select and copy the outline.');}}
 },{signal:control.signal});
 return {dispose(){control.abort();}};
}
