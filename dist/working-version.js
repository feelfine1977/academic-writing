// A separate draft must never silently replace a retained passage in a preview.
export function workingVersion(selected,draft,useFresh=false){
 if(selected?.document_id&&!useFresh)return {kind:'retained',text:selected.text,label:'Selected WISE passage · saved copy',editable:false};
 return {kind:'draft',text:draft||'',label:'My working draft · not automatically selected for WISE',editable:true};
}
