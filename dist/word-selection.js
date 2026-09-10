// Keep the full editor snapshot so delayed advice cannot replace a different word.
export function selectedPhrase(text,start,end){
 if(start===end||!text.slice(start,end).trim())return null;
 return {text,start,end,selected:text.slice(start,end),before:text.slice(Math.max(0,start-700),start),after:text.slice(end,end+700)};
}
export function canApplyWord(snapshot,current){return !!snapshot&&snapshot.text===current&&current.slice(snapshot.start,snapshot.end)===snapshot.selected;}
