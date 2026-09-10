// Compare words for review without modifying either stored version.
export function wordChanges(before,after){
 const a=before.match(/\S+/g)||[],b=after.match(/\S+/g)||[];
 const spacingOnly=before!==after&&a.join(' ')===b.join(' '),ops=[];
 const push=(kind,word)=>{if(ops.at(-1)?.kind===kind)ops.at(-1).text+=' '+word;else ops.push({kind,text:word})};
 if(a.length*b.length>2_000_000){
  let left=0,right=0;while(left<a.length&&left<b.length&&a[left]===b[left])left++;
  while(right<a.length-left&&right<b.length-left&&a[a.length-1-right]===b[b.length-1-right])right++;
  for(const w of a.slice(0,left))push('same',w);
  for(const w of a.slice(left,a.length-right))push('removed',w);
  for(const w of b.slice(left,b.length-right))push('added',w);
  for(const w of a.slice(a.length-right))push('same',w);
  return {ops,spacingOnly,coarse:true};
 }
 const width=b.length+1,table=new Uint16Array((a.length+1)*width);
 for(let i=a.length-1;i>=0;i--)for(let j=b.length-1;j>=0;j--)table[i*width+j]=a[i]===b[j]?1+table[(i+1)*width+j+1]:Math.max(table[(i+1)*width+j],table[i*width+j+1]);
 let i=0,j=0;
 while(i<a.length||j<b.length){
  if(i<a.length&&j<b.length&&a[i]===b[j]){push('same',a[i]);i++;j++}
  else if(j<b.length&&(i===a.length||table[i*width+j+1]>table[(i+1)*width+j])){push('added',b[j]);j++}
  else{push('removed',a[i]);i++}
 }
 return {ops,spacingOnly,coarse:false};
}
