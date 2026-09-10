export function discussionScope(text,start=0,end=0,whole=false){
 const selected=!whole&&start!==end;
 return {text,start:selected?start:0,end:selected?end:text.length,selected:selected?text.slice(start,end):text,scope:selected?'Selected text':'Whole paragraph'};
}
export function proposedText(snapshot,option,current){
 if(!snapshot||current!==snapshot.text)return null;
 if(!option.span||!Number.isInteger(option.span.start)||!Number.isInteger(option.span.end)||option.span.end<=option.span.start)return null;
 const start=snapshot.start+option.span.start,end=snapshot.start+option.span.end;
 if(current.slice(start,end)!==option.quote||end>snapshot.end||start<snapshot.start)return null;
 return {text:current.slice(0,start)+option.replacement+current.slice(end),start,end:start+option.replacement.length};
}
export function recoverDiscussion(job,current){
 if(typeof job.original_text==='string'){
  if(current!==job.original_text)return null;
  // Stored positions count Python Unicode characters; editors use UTF-16 units.
  const chars=[...job.original_text],a=job.selection_start,b=job.selection_end;
  if(!Number.isInteger(a)||!Number.isInteger(b)||a<0||b<a||b>chars.length||chars.slice(a,b).join('')!==job.text)return null;
  return discussionScope(current,chars.slice(0,a).join('').length,chars.slice(0,b).join('').length);
 }
 return current===job.text?discussionScope(current):null;
}
export function proposalState(snapshot,option,current){
 const next=proposedText(snapshot,option,current);
 if(!next)return {next:null,notice:!snapshot||current!==snapshot.text?'Your text has changed since this advice. Ask again about the current text; newer edits will not be overwritten.':'The quoted passage could not be located exactly. Select it again and ask for new advice.'};
 const check=option.check;
 const notice=check?.status==='checking'?'The optional meaning check is still running. You can use this as draft wording now and undo it.'
  :check?.status==='unavailable'?'The extra check was unavailable. You can still use this wording in your draft and undo it.'
  :check?.apply_allowed===true?'The comparison found no regression. Apply to your draft only; Undo is available.'
  :check?.status==='needs_attention'?'The comparison raised concerns above. You decide whether to use this wording in your draft; Undo is available.'
  :'This earlier suggestion has no completed meaning check. You can use it as draft wording and undo it.';
 return {next,notice};
}
