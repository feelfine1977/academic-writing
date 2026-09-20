import {mountTextCoach} from './text-coach.js';

// Freeze the card's current writing brief for each question. This creates a
// review snapshot only; it never applies an attempt or changes completion.
export async function preparePaperTutorContext({api,paperId,cardId,current=()=>true,flush}){
 if(!current())throw new Error('Open the current argument before asking the tutor.');
 await flush();
 if(!current())throw new Error('The argument changed while saving. Ask from the current argument.');
 const context=await api(`/workspace/papers/${encodeURIComponent(paperId)}/cards/${encodeURIComponent(cardId)}/practice`,{});
 if(!current())throw new Error('The argument changed while preparing the question. Your draft is saved.');
 if(!context?.exercise_key)throw new Error('The tutor could not prepare this argument. Your draft is saved.');
 return {exerciseKey:context.exercise_key};
}

export function mountPaperDeskTutor({api,esc,editor,host,paperId,cardId,current,flush}){
 return mountTextCoach({
  api,esc,editor,host,current,introNote:'',
  storageKey:`awl-paper-tutor-${paperId}-${cardId}`,
  historyContext:{paper_id:paperId,card_id:cardId},
  prepareRequest:()=>preparePaperTutorContext({api,paperId,cardId,current,flush}),
  contextNote:'Choose one reading: Structure checks your argument, Evidence compares attached quotations, and English helps with wording. Your submitted text is kept intact. Background notes may be shortened; the tutors do not verify original PDFs.',
  presetQuestions:[
   ['Structure','Read my current passage against its purpose, the meeting guidance and the supplied neighbouring drafts. Separate supervisor remarks from AI reviewer suggestions. Identify at most two useful issues and one next writing step. Preserve the distinctions in my current outline. Do not rewrite, redesign my outline or require every planning bullet.','structure'],
   ['Evidence','Check each claim against the attached quotations. Show what is supported, partly supported, or not established by these passages. Explain what is missing and give me a next step. Do not rewrite my paragraph or invent references.','evidence'],
   ['English','Which grammar or wording changes would make my current text easier to read while preserving my meaning and qualifications? Separate necessary corrections from optional style.']
  ]
 });
}
