// A writing brief belongs to the selected outline idea. It is teaching guidance,
// never manuscript text and never a model-generated requirement for completion.
const text=value=>typeof value==='string'?value.trim():'';
const list=value=>Array.isArray(value)?value.map(text).filter(Boolean):text(value)?[text(value)]:[];
const first=(...values)=>values.map(text).find(Boolean)||'';
const titleOf=(step,index)=>first(step?.title,step?.label,step?.name)||`Idea ${index+1}`;
const ownObject=value=>value&&typeof value==='object'&&!Array.isArray(value)?value:{};

export function writingStepGuide(step={}, {index=0,steps=[],stage='connect'}={}){
 step=ownObject(step);
 const guide=ownObject(step.writing_guide),title=titleOf(step,index);
 const purpose=first(step.purpose,step.job,step.message,step.goal,step.text);
 const points=list(step.points||step.bullets||step.claims||step.key_ideas).slice(0,4);
 const bridge=first(step.bridge_question,step.bridge,step.connection,step.bridge_to_next,step.transition);
 const nextStep=Array.isArray(steps)?steps[index+1]:null;
 const nextTitle=nextStep?titleOf(nextStep,index+1):'';
 const custom=Object.keys(guide).length>0;
 const result={
  title,
  goal:first(guide.goal)||`Write this part: ${title}.`,
  write_now:list(guide.write_now),
  reader_needs:first(guide.reader_needs,purpose)||'The main point of this part, expressed in your own words.',
  enough_for_now:first(guide.enough_for_now)||'A connected first version is enough for now. Keep useful wording and leave [check] where a detail needs attention.',
  next:first(guide.next)||(nextTitle?`Continue to “${nextTitle}”. ${bridge}`.trim():'Read this part with the preceding text and check that its place in the section is clear.'),
  guardrail:first(guide.guardrail,step.boundary),
  provenance:list(step.provenance||step.source||step.sources),
  self_review:'After writing, read this part once and improve one unclear connection yourself. Then ask the tutor one specific question if you need help.',
  custom,
  stage:['connect','rewrite','polish'].includes(stage)?stage:'connect',
  label:'Writing guide · separate from your draft'
 };
 if(!result.write_now.length)result.write_now=points.length?points:[purpose||`Write the point you want the reader to take from “${title}”.`];
 if(result.stage==='rewrite'){
  result.goal=`Revise the connection in “${title}”.`;
  result.write_now=[`Read the sentences you wrote for “${title}” together with the previous passage.`,`Keep the parts that already convey your point. Rewrite a jump or unclear reference in your own words.`];
  result.enough_for_now='One clearer passage is progress. Keep the rest and continue; you do not need to restart the section.';
 }else if(result.stage==='polish'){
  result.goal=`Polish one passage in “${title}”.`;
  result.write_now=['Choose one sentence that feels hard to read. Shorten or split it while keeping the same claim.','Read it beside the surrounding sentences. Keep technical terms, uncertainty, conditions and references stable.'];
  result.enough_for_now='A clearer sentence with the same meaning is enough for this pass.';
 }
 return result;
}

export function writingStartMarkup(guide,esc){
 if(typeof esc!=='function')throw new TypeError('A text escaping function is required.');
 return `<div class="sw-writing-brief"><span class="sw-kicker">${esc(guide.label)}</span><h3>${esc(guide.goal)}</h3><p class="sw-reader-needs"><strong>What the reader needs here</strong><br>${esc(guide.reader_needs)}</p><ol class="sw-write-now">${guide.write_now.map(item=>`<li>${esc(item)}</li>`).join('')}</ol><p class="sw-enough"><strong>Enough for now:</strong> ${esc(guide.enough_for_now)}</p><details class="sw-writing-next"><summary>After this part</summary><p>${esc(guide.next)}</p><p>${esc(guide.self_review)}</p>${guide.guardrail?`<p><strong>Keep in mind:</strong> ${esc(guide.guardrail)}</p>`:''}</details></div>`;
}
