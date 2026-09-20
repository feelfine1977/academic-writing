// A read-only Markdown view. Stored source text and manuscript fields are never changed.
const escapeHTML=(s='')=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function safeReadingURL(value){
 try{
  const s=String(value).trim();if(/[\u0000-\u001f\u007f]/.test(s))return null;
  if(/^#papers\/[\w-]+(?:\?card=[\w-]+)?$/.test(s))return s;
  const u=new URL(s);
  if(['http:','https:'].includes(u.protocol))return u.href;
  if(u.protocol==='obsidian:'&&u.hostname==='open'&&['','/'].includes(u.pathname)&&u.searchParams.get('vault')&&u.searchParams.get('file'))return u.href;
 }catch{}return null;
}
export function paperLinkResolver(note,plan={}){
 return (target,{wiki=false}={})=>{
  const direct=safeReadingURL(target);if(direct)return direct;
  if(/^[a-z][a-z0-9+.-]*:/i.test(target)||target.startsWith('/'))return null;
  try{
   const uri=new URL(note.uri),base=uri.searchParams.get('file');if(!base)return null;
   const [path,...fragment]=decodeURIComponent(target).split('#');
   const parts=wiki?[]:base.split('/').slice(0,-1);
   for(const part of path.split('/')){if(part==='..'){if(!parts.length)return null;parts.pop()}else if(part&&part!=='.')parts.push(part)}
   const resolved=(path?parts.join('/'):base)+(fragment.length?'#'+fragment.join('#'):'');
   for(const item of [plan,...(plan.nodes||[]),...(plan.unplaced||[])]){
    if(item.uri&&new URL(item.uri).searchParams.get('file')===resolved)return '#papers/'+encodeURIComponent(plan.id)+(item.id===plan.id?'':'?card='+encodeURIComponent(item.id));
   }
   uri.searchParams.set('file',resolved);return safeReadingURL(uri.href);
  }catch{return null}
 };
}
function inline(text,resolve,depth=0){
 if(depth>8)return escapeHTML(text);let out='',i=0;
 while(i<text.length){
  if(text[i]==='\\'&&i+1<text.length){out+=escapeHTML(text[i+1]);i+=2;continue}
  if(text[i]==='`'){
   const end=text.indexOf('`',i+1);if(end>i+1){out+='<code>'+escapeHTML(text.slice(i+1,end))+'</code>';i=end+1;continue}
  }
  const image=text[i]==='!',start=image?i+1:i;
  if(text.startsWith('[[',start)){
   const end=text.indexOf(']]',start+2);if(end!==-1){const [target,...label]=text.slice(start+2,end).split('|');const name=label.join('|')||target;const href=safeReadingURL(resolve(target,{wiki:true}));out+=href?`<a class="${href.startsWith('obsidian:')?'paper-obsidian-link':''}" href="${escapeHTML(href)}">${image?'Open figure: ':''}${escapeHTML(name)}</a>`:escapeHTML(name);i=end+2;continue}
  }
  if(text[start]==='['){
   const close=text.indexOf('](',start+1);
   if(close!==-1){let j=close+2,level=1,angle=text[j]==='<';if(angle){j=text.indexOf('>)',j);if(j!==-1)j++}else{for(;j<text.length;j++){if(text[j]==='\\'){j++;continue}if(text[j]==='(')level++;if(text[j]===')'&&!--level)break}}
    if(j!==-1&&j<text.length&&text[j]===')'){let target=text.slice(close+2,j);if(target.startsWith('<')&&target.endsWith('>'))target=target.slice(1,-1);const label=text.slice(start+1,close),href=safeReadingURL(resolve(target));out+=href?`<a class="${href.startsWith('obsidian:')?'paper-obsidian-link':''}" href="${escapeHTML(href)}">${image?'Open figure: ':''}${inline(label,resolve,depth+1)}</a>`:inline(label,resolve,depth+1);i=j+1;continue}
   }
  }
  let formatted=false;
  for(const [mark,tag] of [['**','strong'],['__','strong'],['==','mark'],['*','em'],['_','em']]){
   if(text.startsWith(mark,i)&&!(mark==='_'&&/\w/.test(text[i-1]||''))){const end=text.indexOf(mark,i+mark.length);if(end>i+mark.length){out+=`<${tag}>`+inline(text.slice(i+mark.length,end),resolve,depth+1)+`</${tag}>`;i=end+mark.length;formatted=true;break}}
  }
  if(!formatted){out+=escapeHTML(text[i]);i++}
 }return out;
}
export function renderPaperMarkdown(value,{resolve=safeReadingURL}={}){
 const lines=String(value||'').replace(/\r\n?/g,'\n').split('\n');let out='',i=0;
 const cellRow=line=>line.trim().replace(/^\|/,'').replace(/\|$/,'').split(/(?<!\\)\|/).map(s=>s.trim().replace(/\\\|/g,'|'));
 const block=line=>/^(#{1,6}\s|\s*>|\s*[-*+]\s|\s*\d+[.)]\s|```)/.test(line);
 while(i<lines.length){
  const line=lines[i];if(!line.trim()){i++;continue}
  if(/^```/.test(line)){let code=[];i++;while(i<lines.length&&!/^```/.test(lines[i]))code.push(lines[i++]);i++;out+='<pre><code>'+escapeHTML(code.join('\n'))+'</code></pre>';continue}
  const heading=line.match(/^(#{1,6})\s+(.+)/);if(heading){const level=Math.max(2,heading[1].length);out+=`<h${level}>${inline(heading[2],resolve)}</h${level}>`;i++;continue}
  if(/^\s*>/.test(line)){const quote=[];while(i<lines.length&&/^\s*>/.test(lines[i]))quote.push(lines[i++].replace(/^\s*>\s?/,''));const callout=quote[0]?.match(/^\[!(\w+)\]\s*(.*)/);if(callout){quote.shift();out+=`<aside class="paper-reading-callout"><strong>${escapeHTML(callout[2]||callout[1])}</strong>${renderPaperMarkdown(quote.join('\n'),{resolve})}</aside>`}else out+='<blockquote>'+renderPaperMarkdown(quote.join('\n'),{resolve})+'</blockquote>';continue}
  if(line.includes('|')&&i+1<lines.length&&/^\s*\|?\s*:?-{3,}/.test(lines[i+1])){
   const headers=cellRow(line);i+=2;let rows='';while(i<lines.length&&lines[i].includes('|')&&lines[i].trim())rows+='<tr>'+cellRow(lines[i++]).map(c=>'<td>'+inline(c,resolve)+'</td>').join('')+'</tr>';
   out+='<div class="paper-reading-table" role="region" aria-label="Source table" tabindex="0"><table><thead><tr>'+headers.map(c=>'<th scope="col">'+inline(c,resolve)+'</th>').join('')+'</tr></thead><tbody>'+rows+'</tbody></table></div>';continue
  }
  const list=line.match(/^\s*([-*+]|\d+[.)])\s+(.*)/);if(list){const numbered=/\d/.test(list[1]),tag=numbered?'ol':'ul';let items='';while(i<lines.length){const m=lines[i].match(/^\s*([-*+]|\d+[.)])\s+(.*)/);if(!m||/\d/.test(m[1])!==numbered)break;items+='<li>'+inline(m[2],resolve)+'</li>';i++}out+=`<${tag}>${items}</${tag}>`;continue}
  const paragraph=[line];i++;while(i<lines.length&&lines[i].trim()&&!block(lines[i])){if(lines[i].includes('|')&&i+1<lines.length&&/^\s*\|?\s*:?-{3,}/.test(lines[i+1]))break;paragraph.push(lines[i++])}
  const text=paragraph.join('\n'),kind=/^\*\*(Printed page|PDF page|Page|Source and page)/i.test(text)?' paper-reading-pages':/^\*\*(Use with care|Limit|Boundary)/i.test(text)?' paper-reading-limit':/^\*\*(Context|Supports|Relevance)/i.test(text)?' paper-reading-context':'';
  out+=`<p class="${kind.trim()}">`+inline(text,resolve).replaceAll('\n','<br>')+'</p>';
 }
 return out;
}
