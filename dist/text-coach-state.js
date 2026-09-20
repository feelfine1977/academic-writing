export function discussionScope(text,start=0,end=0,whole=false){
 const selected=!whole&&start!==end;
 return {text,start:selected?start:0,end:selected?end:text.length,selected:selected?text.slice(start,end):text,scope:selected?'Selected text':'Whole paragraph'};
}
function originalSpan(snapshot,option){
 if(!snapshot||typeof snapshot.text!=='string'||!Number.isInteger(snapshot.start)||!Number.isInteger(snapshot.end)||snapshot.start<0||snapshot.end>snapshot.text.length||snapshot.end<snapshot.start)return null;
 if(!option?.span||!Number.isInteger(option.span.start)||!Number.isInteger(option.span.end)||option.span.end<=option.span.start)return null;
 if(typeof option.quote!=='string'||!option.quote||typeof option.replacement!=='string'||!option.replacement.trim()||option.replacement===option.quote)return null;
 const start=snapshot.start+option.span.start,end=snapshot.start+option.span.end;
 if(snapshot.text.slice(start,end)!==option.quote||end>snapshot.end||start<snapshot.start)return null;
 return {start,end,quote:option.quote,replacement:option.replacement};
}
function recognisedEdits(snapshot,options,current){
 if(!snapshot)return null;
 if(current===snapshot.text)return [];
 // A response has at most three proposals. Reconstruct only exact combinations
 // of its edits, so reopening advice cannot replace an unrelated occurrence or
 // silently absorb manual changes. Keep the submitted snapshot immutable.
 if(!Array.isArray(options)||options.length>8)return null;
 const spans=options.map(o=>originalSpan(snapshot,o)).filter(Boolean);
 let match=null;
 for(let mask=1;mask<2**spans.length;mask++){
  const edits=spans.filter((_,i)=>mask&(1<<i)).sort((a,b)=>a.start-b.start);
  if(edits.some((e,i)=>i&&e.start<edits[i-1].end))continue;
  let candidate='',cursor=0;
  for(const e of edits){candidate+=snapshot.text.slice(cursor,e.start)+e.replacement;cursor=e.end}
  candidate+=snapshot.text.slice(cursor);
  if(candidate!==current)continue;
  if(match)return null; // Ambiguous combinations need a fresh question.
  match=edits;
 }
 return match;
}
function resolveProposal(snapshot,option,current,options){
 const span=originalSpan(snapshot,option);
 if(!span)return {reason:'invalid'};
 const edits=recognisedEdits(snapshot,options,current);
 if(!edits)return {reason:'changed'};
 if(edits.some(e=>e.start===span.start&&e.end===span.end&&e.replacement===span.replacement))return {reason:'applied'};
 if(edits.some(e=>e.start<span.end&&e.end>span.start))return {reason:'overlap'};
 const shift=edits.filter(e=>e.end<=span.start).reduce((sum,e)=>sum+e.replacement.length-(e.end-e.start),0);
 const start=span.start+shift,end=span.end+shift;
 if(current.slice(start,end)!==option.quote)return {reason:'changed'};
 return {next:{text:current.slice(0,start)+option.replacement+current.slice(end),start,end:start+option.replacement.length},rebased:edits.length>0};
}
export function proposedText(snapshot,option,current,options=[]){
 return resolveProposal(snapshot,option,current,options).next||null;
}
export function recoverDiscussion(job,current){
 if(typeof job.original_text==='string'){
  // Stored positions count Python Unicode characters; editors use UTF-16 units.
  const chars=[...job.original_text],a=job.selection_start,b=job.selection_end;
  if(!Number.isInteger(a)||!Number.isInteger(b)||a<0||b<a||b>chars.length||chars.slice(a,b).join('')!==job.text)return null;
  const snapshot=discussionScope(job.original_text,chars.slice(0,a).join('').length,chars.slice(0,b).join('').length);
  return recognisedEdits(snapshot,job.result?.suggestions||[],current)?snapshot:null;
 }
 return current===job.text?discussionScope(current):null;
}
export function proposalState(snapshot,option,current,options=[]){
 const resolved=resolveProposal(snapshot,option,current,options),next=resolved.next;
 if(!next){
  const notices={applied:'This suggestion is already in your draft.',overlap:'This suggestion overlaps wording you already changed with another suggestion. Undo that edit or ask again about this passage.',changed:'Your draft contains other changes that could not be matched safely to these suggestions. Ask again about the current text; newer edits will not be overwritten.',invalid:'The quoted passage could not be located exactly. Select it again and ask for new advice.'};
  return {next:null,applied:resolved.reason==='applied',notice:notices[resolved.reason]};
 }
 const check=option.check;
 const notice=check?.status==='checking'?'The optional meaning check is still running. You can use this as draft wording now and undo it.'
  :check?.status==='unavailable'?'The extra check was unavailable. You can still use this wording in your draft and undo it.'
  :check?.apply_allowed===true?'The comparison found no regression. Apply to your draft only; Undo is available.'
  :check?.status==='needs_attention'?'The comparison raised concerns above. You decide whether to use this wording in your draft; Undo is available.'
  :'This earlier suggestion has no completed meaning check. You can use it as draft wording and undo it.';
 return {next,notice:(resolved.rebased?'This passage is unchanged. Earlier suggested edits will be kept. ':'')+notice};
}
