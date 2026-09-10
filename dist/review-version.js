// A review always belongs to one immutable submission, even while its editor changes.
export function reviewVersionNote(job,attempt,draft,number){
 const version=number>0?`attempt ${number}`:'the submitted version';
 if(!attempt)return `This feedback refers to ${version}. Your editor stays editable.`;
 const pending=['queued','running'].includes(job.status),changed=draft!==attempt.text;
 return `${pending?'The tutor is reading':'This feedback refers to'} ${version}. ${changed?'Your text has changed since that submission. Save & get feedback when you want these changes reviewed.':pending?'You can edit now; both readings will still assess that saved text.':'Your editor matches the reviewed text. You can revise it here.'}`;
}
