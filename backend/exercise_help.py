"""Plain-language teaching overlay. Does not alter versioned questions or marking keys."""
import copy
import json
import re

VERSION='2026-09-10.1'
# Each explanation includes an original example outside the learner's research field.
GLOSSARY=[
 ('actor','Who or what performs an action. It can be a person, organisation or tool; use only what the facts identify.','The curator shortened the labels: the curator performs the action.'),
 ('referent','The person, thing or idea that a word such as it, they, their or this points to. It is not simply the object after a verb.','The curator shortened the labels. Visitors read them: them refers to the labels.'),
 ('demonstrative','A pointing word: this, that, these or those. Adding a noun can tell the reader exactly what you mean.','Replace an unclear This helped with This change in opening hours helped, if that is the change you mean.'),
 ('reference','A link back to a person, thing or idea in the text. In citation tasks, a reference instead identifies a source.','The tickets arrived. They were blue: they points back to the tickets.'),
 ('antecedent','The earlier word or phrase that a later word points back to.','In The tickets arrived; they were blue, tickets is the earlier word that they refers to.'),
 ('subject','The person or thing that a sentence or clause makes a statement about. In a passive sentence it need not perform the action.','The labels were shortened by the curator: the labels is the subject; the curator did the shortening.'),
 ('head of the subject','The main noun or pronoun in the subject. Extra description does not change whether that main word is singular or plural.','The labels beside the entrance are short: labels is the main noun, so use are.'),
 ('clause','A group of words containing a subject and a verb. Some clauses need another clause to make a complete sentence.','Although the museum is small is a clause that needs a main statement, such as it attracts many visitors.'),
 ('noun phrase','A group of words built around a noun. It names a person, thing or idea.','The small museum near the station is a noun phrase; museum is its main noun.'),
 ('complement','Words that a verb or other expression needs to complete its meaning.','The ticket allows visitors to enter: visitors to enter completes what allows means here.'),
 ('modifier','A word or phrase that adds detail to, or limits, another part of a sentence.','Only damaged apples were weighed: only limits which apples were weighed.'),
 ('relative clause','A clause beginning with a word such as who, which or that, giving information about a noun.','The visitors who booked online entered first: who booked online identifies which visitors.'),
 ('passive voice','A sentence form in which the subject receives the action. Use it when that subject is the useful focus.','The labels were shortened by the curator. The labels receive the action.'),
 ('active voice','A sentence form in which the subject performs the action.','The curator shortened the labels. The subject, curator, performs the action.'),
 ('tense','A verb form that helps place a statement in time, such as past or present.','We tested the lamps reports completed work; we will test them describes a plan.'),
 ('agreement','Matching a verb or pronoun to the number or person of the words it belongs with.','The label is clear; the labels are clear.'),
 ('collocation','Words that conventionally occur together in a particular meaning.','We conduct a survey and draw a conclusion; the choice depends on what we mean.'),
 ('register','The kind of language suited to the audience and purpose. Academic language can be direct and familiar.','We measured the room is appropriate in a methods section; longer words are not automatically better.'),
 ('reporting verb','A verb that tells readers what a source did: reported, proposed, argued or demonstrated.','The historian proposed an explanation describes a suggestion, not a verified result.'),
 ('stance','The position a writer takes towards a claim, including confidence, agreement or doubt.','The author proposes a cause keeps more distance than The author establishes the cause.'),
 ('diagnosis','An explanation of what works or causes difficulty in a piece of writing, and why. It is different from just rewriting it.','This helped is unclear because this could mean the new chairs or longer opening hours. Name the intended change.'),
 ('consequential span','A short, exact part of the text whose wording matters to the meaning.','In All visitors preferred mornings, quote All visitors if the survey only covered ten respondents.'),
 ('proposition','A statement that can be discussed as true or false.','The museum closes at four is one proposition; it has a large collection is another.'),
 ('claim','Something the writer asks the reader to accept as true.','The new signs reduced waiting is a claim that needs suitable evidence.'),
 ('scope','The people, cases, conditions or settings to which a claim applies.','Among the 20 people surveyed limits the statement to that group.'),
 ('quantifier','A word that says how many or how much, such as all, some, none or most.','Not all tickets sold means some remained; it does not mean that none sold.'),
 ('negation','Wording that makes a statement negative, usually with no or not. Check exactly what it denies.','Not every room was tested leaves open whether some rooms were tested.'),
 ('premise','A fact or assumption used as a starting point for a conclusion.','Only six beds can be inspected today is a starting point for discussing inspection order.'),
 ('warrant','The reason that makes evidence relevant to a conclusion. Explain this reason instead of just adding therefore.','If reading a label is necessary to use its instructions, reading frequency is relevant to whether the instructions reach visitors.'),
 ('bridge','The missing explanation that connects two ideas, or carries one paragraph into the next.','Only six of ten beds can be checked today. Because four must wait, the gardener needs a rule for deciding which checks come first.'),
 ('connective','A word or phrase such as because, although or therefore that signals a relationship. It cannot supply a missing reason.','Because the room has reached its capacity, entry must wait states the reason as well as the connection.'),
 ('concession','Accepting one point while explaining why it does not settle the whole question.','Although the museum has a large collection, its short opening hours limit evening access.'),
 ('qualification','A condition or limit that makes a statement more precise.','The lamp lasted eight hours under the tested conditions limits what the result establishes.'),
 ('hedge','Wording that expresses a justified degree of uncertainty, such as may or suggests. Explain what is uncertain.','Longer stays may reflect the new chairs: the stays were observed, but the explanation is uncertain.'),
 ('inference','A conclusion you draw from observations or other information, rather than an observation itself.','Sold tickets show purchases; concluding that every buyer attended is an extra step.'),
 ('attribution','Making clear whose finding, claim or interpretation you are reporting.','Source A reports ticket sales. Our interpretation concerns possible demand: the two statements have different owners.'),
 ('synthesis','Connecting sources around a shared question and explaining their agreement, difference or combined limits.','One study measures reading time and another tests recall; together they examine different aspects of engagement.'),
 ('research gap','A specific unresolved question in the work you have actually examined.','None of the 12 inspected catalogues gives a relocation date is a bounded gap; no historian knows the date is much broader.'),
 ('causal','Concerning whether one thing produces a change in another.','Attendance rose after prices fell does not by itself show that the price change caused the rise.'),
 ('causality','The relationship in which one thing produces a change in another.','A new performer arrived when prices fell; the observed attendance change does not isolate either cause.'),
 ('association','Things occurring or varying together, without necessarily showing that one causes the other.','Umbrella use and wet pavements occur together; umbrella use does not make the pavement wet.'),
 ('mechanism','The process through which something is proposed to work. Describe it as a hypothesis if it has not been tested.','A reminder might increase attendance by helping people remember the date; that explanation still needs evidence.'),
 ('intervention','A deliberate change intended to affect an outcome. Choosing what to investigate is a separate decision.','Inspecting a crowded entrance gathers information; opening a second entrance changes the situation.'),
 ('necessary condition','A requirement that must hold, but may not be enough by itself.','A valid ticket is required for entry, but entry also depends on room capacity.'),
 ('sufficient condition','A condition that is enough to establish a stated outcome under the specified rules.','If the only entry rule is a valid ticket, having one is enough under that rule.'),
 ('guardrail','A mandatory limit or requirement that other advantages cannot cancel out.','A room capacity of 50 must be respected even if more tickets could be sold.'),
 ('operational definition','An exact rule for identifying or measuring something in this study.','Count each admission as one visit: a person admitted twice contributes two visits.'),
 ('unit','What is being counted, measured or analysed. It can also mean a measurement scale.','Visits and visitors count different things; minutes is a unit for duration.'),
 ('denominator','The number below a fraction, or the total against which a proportion is calculated.','In 36 of 60 respondents, 60 is the denominator. Do not replace respondents with all visitors.'),
 ('baseline','The starting value or comparison used to interpret a change.','A rise from 20% to 30% uses 20% as its starting value.'),
 ('percentage points','The direct difference between two percentages.','A rise from 20% to 30% is 10 percentage points, or 50% relative to the earlier 20%.'),
 ('statistical significance','An assessment of compatibility with a statistical model or hypothesis under stated assumptions. It does not by itself establish practical importance.','A reported difference alone is not enough to call the result statistically significant.'),
 ('empirical','Based on observation or measurement. A planned benefit is not yet an observed result.','Thirty-six respondents preferred mornings is an observation; longer opening will increase revenue is not established by it.'),
 ('rationale','The reason for choosing something, connected to your actual purpose.','We used a portable meter because the study required measurements in several rooms.'),
 ('trade-off','A choice in which gaining something comes with a cost on another dimension.','Displaying more objects may leave less space for detailed labels.'),
 ('transition','Wording that tells readers how the next idea relates to the previous one.','Having established demand for evening buses, we next examine staffing requirements.'),
 ('handover','The point at which one paragraph gives the next a question or idea to develop.','A paragraph establishes a need for evening access; the next asks how to staff it.'),
 ('information flow','The order in which sentences introduce and develop ideas so readers can follow them.','Introduce a shared watering schedule, then explain what that schedule records.'),
 ('counterargument','A relevant objection to a claim. Represent it fairly before responding.','Moisture sensors miss some diseases is a fair limit; explain whether disease detection was the intended task.'),
 ('concision','Using no more words than the meaning needs, while keeping necessary conditions and limits.','We tested typed records keeps a key limit that We tested records would lose.'),
 ('editorial note','A short explanation of your writing decisions, separate from the passage itself.','I kept the sample size because it limits how broadly the result can be interpreted.'),
 ('evidence boundary','The limit of what the available observations can establish.','A survey of preferences does not establish actual attendance or staffing costs.'),
 ('recoverable','Clear enough that the reader can work out the intended meaning from the text.','After The curator shortened the labels, them is recoverable in Visitors read them.'),
 ('nominalisation','A noun formed from a verb or adjective. Sometimes a verb makes the action easier to follow.','We evaluated the lamps can be clearer than An evaluation of the lamps was performed.'),
 ('parallel structure','Using matching grammatical patterns for comparable items.','We measured height, recorded weight and counted seeds uses three matching verb phrases.'),
 ('article','The words a, an and the, used with nouns to help identify what you mean.','A visitor entered introduces someone; the visitor sat down refers to that person again.'),
 ('preposition','A word such as in, on, at or by that expresses a relationship. Some expressions conventionally take particular prepositions.','The label is on the wall; the result depends on the lighting.'),
 ('rhetorical move','The job a part of the writing does for the reader, such as defining a term or explaining a limitation.','Before discussing visitor counts, a sentence defines what counts as one visit.'),
 ('evidence ledger','A small record that keeps a claim, its supporting evidence and its limits together.','Claim: respondents prefer mornings. Evidence: 36 of 60 chose mornings. Limit: actual bookings were not measured.'),
 ('reproducible','Described precisely enough that someone else can repeat the procedure with the relevant materials and settings.','State which rooms were measured, with which meter and for how long, rather than We measured carefully.'),
 ('uncountable','Normally used as an amount rather than separate items in this meaning.','Evidence is uncountable in ordinary academic usage: evidence is limited, or two pieces of evidence.'),
 ('countable','Used for separate items that can be counted in this meaning.','One visit and two visits are countable; each admission can be counted separately.'),
]

OPERATIONS={
 'diagnose':('Explain the wording in 3–5 sentences. Quote the part that matters, explain what a reader could misunderstand, and use the supplied facts to resolve it. Your answer is an explanation, not just a replacement passage.',[
  'Read the facts, then the draft. Highlight the exact words that change or obscure the meaning.',
  'Start with a short quotation: “…” is unclear / too strong / accurate because … .',
  'Name the fact that resolves the problem. Say whether it concerns meaning, grammar, or an optional style choice.',
  'Read your answer as an explanation to the writer. A repaired sentence alone does not complete this task.']),
 'draft':('Write a new passage of 2–4 connected sentences from the supplied facts. Keep the people, quantities and limits accurate; use your own wording.',[
  'Choose the main point your reader needs to understand.',
  'Add the fact that supports that point and explain the connection.',
  'Include the condition or uncertainty that limits the claim. Check the requested sentence count.']),
 'review':('Decide whether to keep the proposed wording, revise it, or request evidence. Quote a relevant part and explain your decision in 3–5 sentences. Offer a short correction only when needed.',[
  'Compare the proposed revision with the supplied facts, one claim at a time.',
  'Write Keep, Revise, or Request evidence, then quote the words behind your decision.',
  'Explain what those words preserve, change or assume. Do not invent a fault merely to offer a correction.']),
 'brief':('Write two labelled parts: Brief (at most 60 words) and Editorial note (2–3 sentences). The brief presents the argument; the note explains your writing choices.',[
  'Plan the main point, its support and its limit before writing the brief.',
  'Label the passage Brief: and keep that part within 60 words.',
  'Add Editorial note: and explain which detail you retained and which possible overclaim you avoided.']),
}
STAGES={
 1:('Explain the job this paragraph must do for its reader.', ['Ask what the reader should understand after this paragraph.', 'Describe that purpose in one clear sentence; use the length requested below.']),
 2:('Arrange the supplied argument parts into a useful order.', ['Identify the starting point, supporting reason and final point.', 'Select each supplied part once. You can click parts or type their letters with spaces.']),
 3:('Define one concept: say what it means here and where its limits lie.', ['Choose the term the reader needs before the next claim.', 'State what counts as an instance; distinguish it from a related idea.']),
 4:('Make it clear who or what each sentence is about and, where known, who performs the action.', ['Find the main verb and ask who or what does it.', 'Name that person, organisation or tool only if the supplied facts identify it.']),
 5:('Write only the missing linking reason in one or two sentences.', ['Choose two different ideas from the list.', 'Ask: why does the first idea support, limit or create a need for the second?', 'Write that reason. Adding therefore by itself does not explain the connection.']),
 6:('Identify which claim needs evidence and what evidence would support it.', ['Separate something observed from an explanation or hoped-for benefit.', 'Name the observation, source or test needed. Do not invent a citation or result.']),
 7:('Write a useful condition, contrast or limitation that makes the claim precise.', ['Identify what is true and what that fact does not establish.', 'Connect the points with suitable wording, such as although or under these conditions.']),
 8:('Plan how this paragraph leads to the next one.', ['Name the point established here and the question still open.', 'Explain why the next paragraph needs to answer that question.']),
 9:('Write this paragraph from your idea outline in your own words.', ['Choose a main point and the evidence or reason that supports it.', 'Close earlier prose and write from the ideas.', 'Check the paragraph against its purpose, limits and the length requested below.']),
 10:('Use the same writing skill on a different topic.', ['Identify the relationship you practised, such as a contrast or explanation.', 'Choose another setting and write new content that uses that relationship.', 'Keep invented practice facts separate from claims about your paper.']),
}
FORMATS={
 'gap':('Enter the missing word or words; use / between separate gaps.', ['Read the whole sentence before choosing.', 'Identify the word that controls the missing form, such as the main subject or a verb pattern.', 'Insert your choice mentally and read the sentence again.']),
 'ordering':('Arrange every supplied part once to form the requested sentence or outline.', ['Find a possible beginning and what must follow it.', 'Click the parts in order or type their letters with spaces; no arrows are needed.', 'Read the assembled result and check the logical link and punctuation.']),
 'clause_completion':('Complete the supplied beginning with your own wording. You can enter the missing part or the whole sentence.', ['Read the supplied beginning and identify the relationship it asks for.', 'Use the idea words to form a clause with a subject and verb.', 'Read both parts together; preserve the contrast or condition.']),
 'keywords_to_sentence':('Use the supplied ideas or key words to write a grammatical sentence.', ['Decide who or what the sentence is about.', 'Choose the main verb and connect the remaining ideas.', 'Change word forms and add connecting words as permitted by the prompt.']),
 'outline_to_sentences':('Turn the supplied ideas into connected sentences. Follow the length and specific action in the task below.', ['Identify the main point and which details explain or limit it.', 'State the relationship rather than simply joining the bullet points.', 'Check that each reference points clearly to a named person, thing or idea.']),
 'paragraph_from_ideas':('Write a paragraph from the ideas you have checked, using your own structure and wording.', ['Choose one main point for this paragraph.', 'Add its support, explain the connection, and retain the important limit.', 'Check that the next sentence develops what the reader has just learned.']),
 'free_writing':('Write your own response to the task below. Use its requested form and length; do not copy the example.', ['Identify whether the task asks you to explain, argue, review or draft.', 'Plan the main point, the supporting reason and any limit.', 'Check the criteria after writing and revise only what needs attention.']),
}

TOPIC_HELP={
 'Define the concept and its boundary':('Define the concept for this scenario and explain what it does not include.', ['Say what counts as an instance here.', 'Give the boundary that distinguishes it from a neighbouring idea.']),
 'Separate observation and interpretation':('Write the observation separately from your interpretation of it.', ['State exactly what was recorded.', 'Explain what you infer and what the observation cannot establish.']),
 'Explain why the next check is needed':('Explain which uncertainty makes the next investigation necessary.', ['Name the missing information.', 'Show how the proposed check could address it without promising a result.']),
 'Express the same concession in two forms':('Express the same contrast using the two forms requested in the prompt.', ['Identify the accepted fact and the point that limits its implication.', 'Keep the meaning unchanged when moving between although plus a clause and despite plus a noun phrase or -ing form.']),
 'Describe a reproducible three-step method':('Describe three actions precisely enough for another researcher to follow.', ['Put the actions in their actual order.', 'For each action name the input, the action and the output; retain relevant settings.']),
 'Plan a fair comparison':('Explain what should be compared and how to keep the comparison fair.', ['Name the shared outcome or dimension.', 'Identify which conditions must match and which differences would limit your conclusion.']),
 'Write a bounded result claim':('State the result with its relevant population, units and limits.', ['Name the observed quantity and who or what was measured.', 'Keep any explanation separate and avoid extending the result to untested settings.']),
 'Replace vague reference with a clear connection':('Make clear what a word such as this or they points to.', ['List the possible earlier things the word could mean.', 'Use the supplied facts to choose the intended one; name it without inventing an action or cause.']),
 'Build a small evidence ledger':('Make a short record of the claim, its evidence and what remains unestablished.', ['Pair each claim with its actual supporting observation or source.', 'Record the limit or question beside it; leave missing evidence marked as missing.']),
 'Build a short paragraph from the evidence':('Turn the evidence into a connected paragraph, using the requested length.', ['Choose a main point and the observation that supports it.', 'Explain their relationship and retain the limit on what can be concluded.']),
 'Develop a bounded research argument':('Build an argument that stays within what the supplied evidence can support.', ['State the main claim and its evidence.', 'Explain why that evidence supports the claim, then name the remaining limit.']),
 'Compare competing explanations':('Compare plausible explanations without presenting an untested one as the cause.', ['Name the observations each explanation could account for.', 'Identify the additional evidence that could distinguish the explanations.']),
 'Synthesise two methodological contributions':('Connect the two contributions around a shared research question.', ['Identify what each contribution supplies.', 'Explain where they complement or differ from each other and which issue remains open.']),
 'Justify a choice under a constraint':('Explain why a choice fits the goal given the stated restriction.', ['Name the goal and the requirement that must be respected.', 'Explain the relevant advantage and the cost or limitation you accept.']),
 'Answer a counterargument fairly':('State the objection accurately, then answer it with a reasoned distinction or evidence.', ['Identify which part of the objection is valid.', 'Explain the narrower claim you can defend; do not invent a capability to dismiss the objection.']),
 'Separate uncertainty, limitation and future work':('Distinguish what is unknown, why this study leaves it unknown, and how to investigate it next.', ['Tie the uncertainty to a specific feature of the study.', 'Propose a next test that addresses that feature without implying it is already complete.']),
 'Build a two-paragraph progression':('Write two paragraphs with different jobs and a clear connection.', ['Decide what the first paragraph establishes.', 'Let the second answer a question raised by the first; write a bridge explaining that connection.']),
 'Respond to a reviewer with a revision plan':('Acknowledge the reviewer’s concern and state the concrete revision you propose.', ['Identify the claim or explanation that needs attention.', 'Say what will change and why. Describe unperformed work as planned, not completed.']),
 'Revise inflated prose without losing the idea':('Make the passage more direct while keeping its argument and important limits.', ['Identify the claim, the action and the conditions that must survive.', 'Remove repetition and empty framing; compare the meaning before and after.']),
 'Transfer the skill to a new research setting':('Apply the same writing skill to a different research setting.', ['Identify the writing move, such as comparing explanations or bounding a claim.', 'Choose new content and use the same reasoning structure; distinguish invented practice facts from research findings.']),
}

def terms_in(text):
    # Word boundaries avoid e.g. matching actor inside factor or article inside particle.
    found=[{'term':t,'meaning':m,'example':x} for t,m,x in GLOSSARY
           if re.search(r'(?<!\w)'+re.escape(t)+r'(?:s|es)?(?!\w)',text,re.I)]
    return found

def help_for(e,example=None):
    kind=e.get('task_type')
    wise_stage=e.get('stage_index') if e.get('paper_node_id') else None
    topic=TOPIC_HELP.get(e['title']) if e['id'].startswith('AWL-TOPIC-') else None
    output,steps=OPERATIONS.get(kind) or STAGES.get(wise_stage) or topic or FORMATS.get(e['format'],FORMATS['free_writing'])
    if e['format']=='gap' and e.get('choices') and not re.search(r'_{2,}',e['prompt']):
        output='Choose the option that answers the question. Enter the full option as requested below.'
        steps=['Read the question and the supplied facts before comparing the options.',
               'Check each option for the specific distinction the question asks about.',
               'Enter your chosen option and check it against the wording of the question.']
    original=[h.get('text','') if isinstance(h,dict) else str(h) for h in e.get('hints',[])]
    original=[h for h in original if h.strip()]
    hints=[{'title':'Start here','text':steps[0]},
           {'title':'Build your answer','text':' '.join(steps[1:])},
           {'title':'Check this skill','text':'\n'.join(original) or 'Compare your answer with each task criterion. Keep the original facts, conditions and uncertainty.'}]
    text=' '.join([json.dumps(e,ensure_ascii=False),json.dumps(example or {},ensure_ascii=False),output,*steps,*original])
    terms=terms_in(text)
    # Include explanations for terminology introduced by a definition itself.
    expanded=terms_in(' '.join(t['meaning']+' '+t['example'] for t in terms))
    seen={t['term'] for t in terms};terms += [t for t in expanded if t['term'] not in seen]
    primary=' '.join([e.get('learning_objective',''),e.get('title',''),e.get('prompt',''),' '.join(e.get('criteria',[]))]).lower()
    def relevance(t):
        match=re.search(r'(?<!\w)'+re.escape(t['term'])+r'(?:s|es)?(?!\w)',primary)
        return (0,match.start()) if match else (1,0)
    terms.sort(key=relevance)
    return {'version':VERSION,'kind':kind or ('wise-step-'+str(wise_stage) if wise_stage else e['format']),
            'output':output,'steps':steps,'hints':hints,'terms':terms}

def teaching_example(e,original,overrides):
    """Operation-specific examples use separate invented facts, never the task's answer."""
    move=e.get('rhetorical_move');op=e.get('task_type')
    if move not in overrides or op not in OPERATIONS:return copy.deepcopy(original)
    item=overrides[move];facts=item['facts'];repair=item['repair']
    if op=='diagnose':task=f'Facts: {facts}\nDraft to inspect: {item["draft"]}\nExplain the wording in 3–5 sentences.';answer=item['diagnosis']
    elif op=='review':task=f'Facts: {facts}\nProposed wording: {repair}\nDecide whether to keep this wording and explain why.';answer=item['review']
    elif op=='brief':task=f'Facts: {facts}\nWrite a brief of at most 60 words and a separate editorial note.';answer='Brief: '+repair+'\n\nEditorial note: '+item['note']
    else:task=f'Facts: {facts}\nWrite a new passage of 2–4 connected sentences.';answer=repair
    return {'id':f'plain-example-{move}-{op}','subject':original['subject'],'task':task,'answer':answer,
            'moves':item['moves'],'transfer':OPERATIONS[op][0],
            'provenance':'Original invented teaching example from another subject. It demonstrates the answer format; it is not evidence for WISE.'}
