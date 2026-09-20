"""Original fiction exercises, with explicit source provenance and flexible craft criteria."""

SOURCES = [
    {'id':'sanderson-course','title':'Brandon Sanderson · Writing class (2025)', 'url':'https://www.brandonsanderson.com/blogs/blog/brandon-sandersons-writing-class-2025-week-1', 'note':'Official course introduction with the YouTube lecture. Try the tools and adapt them to your process.'},
    {'id':'sanderson-notes','title':'Your PDF · Brandon Sanderson Lecture Series Notes', 'url':'/api/fiction/readings/sanderson-notes', 'note':'Supplied secondary notes, 41 pages; note-taker and lecture year are not established. Plot: pp. 16–22; character: pp. 23–27; setting: pp. 28–31; prose: pp. 12–15 and 32–41.'},
    {'id':'plot-formulas','title':'Your PDF · Plot Formulas', 'url':'/api/fiction/readings/plot-formulas', 'note':'Two-page cheatsheet credited to Eva Deverell. Compares several authors’ frameworks. Page 1 includes Dan Wells’s seven points and the Snowflake method. Treat the formulas as optional lenses.'},
    {'id':'snowflake','title':'Randy Ingermanson · The Snowflake Method', 'url':'https://www.advancedfictionwriting.com/articles/snowflake-method/', 'note':'The method’s creator explains expanding an idea through summaries, characters and scenes. Use only the amount of planning that helps.'},
    {'id':'time-law','title':'Brandon Sanderson · First Law', 'url':'https://www.brandonsanderson.com/blogs/blog/sandersons-first-law', 'note':'Applies reader understanding to solutions involving magic. Using it for time travel is this workshop’s adaptation, not a scientific law.'},
    {'id':'mystery','title':'Writing Excuses 6.26 · Mystery Plotting', 'url':'https://writingexcuses.com/writing-excuses-6-26-mystery-plotting/', 'note':'Plan from the solution; manage when clues are noticed, understood and connected. A conversation about mysteries across genres.'},
    {'id':'romance','title':'Writing Excuses 5.31 · Writing Romance', 'url':'https://writingexcuses.com/writing-excuses-5-31-writing-romance/', 'note':'Build attraction through emotional needs and earned payoff. This episode discusses romantic threads across genres.'},
    {'id':'genre','title':'Writing Excuses 17.1 · Genre and Media are Promises', 'url':'https://writingexcuses.com/17-1-genre-and-media-are-promises/', 'note':'Reader expectations: an optimistic romantic resolution, a contained puzzle and restored security for a cosy mystery. Choose your own content boundaries.'},
    {'id':'humor','title':'Writing Excuses 11.32 · The Element of Humor', 'url':'https://writingexcuses.com/11-32-the-element-of-humor/', 'note':'Expectation, changes in social status, escalation and callbacks can make humour part of the story’s movement.'},
]

TUTORS = [
    {'id':'story','name':'Story architect','initials':'SA','focus':'Premise, causality, reader promises and payoffs. Help the author find one connected story.'},
    {'id':'character','name':'Character coach','initials':'CC','focus':'Motivation, agency, flaws, relationships and change. Ask what a character chooses under pressure.'},
    {'id':'time','name':'Time travel editor','initials':'TE','focus':'World rules, costs, chronology, memory, object provenance and causal consistency. Distinguish story order from calendar order.'},
    {'id':'mystery','name':'Mystery editor','initials':'ME','focus':'Culprit, motive, opportunity, alibis, fair clues and red herrings. Protect the reader’s chance to solve the puzzle.'},
    {'id':'romance','name':'Romance coach','initials':'RC','focus':'Mutual agency, specific attraction, trust, conflict, repair and an earned optimistic ending. Time travel must not erase a partner’s choice.'},
    {'id':'comedy','name':'Comedy coach','initials':'HC','focus':'Character-based incongruity, setup, escalation, timing and callbacks. Keep the author’s chosen warmth and compassion.'},
    {'id':'prose','name':'Scene & prose coach','initials':'PC','focus':'Viewpoint, goal, obstacle, change, subtext, rhythm and clear orientation. Preserve distinctive voice; style preferences are optional.'},
    {'id':'revision','name':'Revision partner','initials':'RP','focus':'Developmental revision before line editing. Check the four genre threads, ending and continuity; distinguish summary review from reading the full manuscript.'},
]

def field(id, label, prompt, example='', rows=3):
    return {'id':id,'label':label,'prompt':prompt,'example':example,'rows':rows}

def stage(id, title, subtitle, tutor, minutes, lesson, exercise, fields, criteria, sources):
    return dict(id=id,title=title,subtitle=subtitle,tutor=tutor,minutes=minutes,lesson=lesson,exercise=exercise,fields=fields,criteria=criteria,sources=sources)

STAGES = [
    stage('spark','Find your story spark','Turn four favourite ingredients into one compelling problem.','story',20,
        'A genre mixture becomes a story when one person wants something, faces resistance and must make a consequential choice. Start small enough to finish. The length target is a planning aid, not a publishing rule. These exercises and examples are original workshop material; the sources below supply craft concepts.',
        'Brainstorm three different premises. Pick the one whose time travel causes both the romantic difficulty and the mystery. Write a single sentence, then a short paragraph that includes an ending you can change later.',[
            field('ideas','Three possible ideas','For each: an unusual time travel constraint + a crime + an awkward romantic situation.', 'A museum tea room repeats Thursday; a missing brooch reappears in tomorrow’s display; the only witness is the curator who thinks you stood them up.'),
            field('logline','Your one-sentence premise','When [disruption], a [specific person] must [goal] despite [obstacle], or [personal cost].'),
            field('synopsis','The whole story in one paragraph','Include the trigger, two complications, the decisive choice and the ending. Spoilers belong here.', rows=5),
        ],['The protagonist has a concrete goal and a personal cost of failure.','Time travel creates a problem that affects the mystery and relationship.','The paragraph reaches a consequence and an ending.'],['sanderson-course','snowflake']),
    stage('promise','Make a promise to your reader','Decide how funny, romantic and cosy this story feels.','story',15,
        'Genre labels create expectations. A romance usually promises a central love story with a happily-ever-after (HEA) or happy-for-now (HFN) ending. A cosy mystery typically combines a contained community, an amateur investigator, restrained on-page violence and restored security. A theft or fraud can support a gentler cosy crime story. Decide your own balance explicitly.',
        'Describe what your reader should feel on page one, in the middle and on the last page. Choose the crime and content boundaries before designing escalating trouble.',[
            field('balance','Your genre balance','Which thread leads: mystery, romance or an equal blend? What do time travel and humour contribute?'),
            field('boundaries','Your cosy boundaries','Choose crime type, on-page violence, intimacy, language, animal safety and the level of peril you want.'),
            field('payoffs','Four promises and their payoffs','Mystery: the answer. Romance: HEA/HFN or a deliberate alternative. Time: the rule and its cost. Humour: the final callback.'),
        ],['Tone and content boundaries are concrete enough to guide a scene.','The planned ending delivers the chosen romantic and mystery promises.','Each genre thread has a visible payoff.'],['genre','sanderson-notes']),
    stage('theme','Find the emotional question','Give the adventure something human to explore.','character',15,
        'Theme grows through choices and consequences. You need not make characters announce a moral. For this combination, a useful tension is whether knowing what happens can replace learning to trust. Your answer can be complicated, and your protagonist need not become an entirely different person.',
        'Give your protagonist an understandable belief that causes trouble. Design two choices: one made from that belief early on and a harder one at the end.',[
            field('question','The question underneath the plot','What human tension do you want to explore? Phrase it as a question, not a slogan.'),
            field('belief','A belief that both helps and hurts','What does your protagonist believe, why is it understandable, and where does it fail?'),
            field('choices','Opening choice → final choice','Give two concrete actions that show change, including what the final action costs.'),
        ],['The theme connects to a character’s specific problem.','An early choice has consequences rather than merely stating a flaw.','The final choice demonstrates an earned change or deliberate refusal to change.'],['sanderson-notes']),
    stage('characters','Build people who make things happen','Map the sleuth, love interest and community.','character',35,
        'Useful character lenses include initiative, competence and relatability. They are adjustable qualities, not scores you must maximise. Give your sleuth a reason to investigate and a skill that matters. The love interest needs their own desire, boundaries and influence on the outcome. Give suspects lives beyond being suspicious.',
        'Make a card for each lead and at least three supporting people. Then write a brief disagreement in which both leads have understandable reasons.',[
            field('sleuth','Your protagonist / amateur sleuth','Name • pronouns • era • public role • concrete want • private need • useful skill • blind spot • reason to investigate • choice at the climax.', rows=5),
            field('partner','Your romantic lead','Name • pronouns • era • independent goal • skill • emotional need • boundary • what attracts each person • a decision only this person can make.', rows=5),
            field('ensemble','Community and relationships','One card per person: name • role • desire • secret • link to both leads • distinct voice. Include allies, suspects and a victim/person harmed.', rows=6),
            field('friction','A disagreement with two reasonable sides','Write 150–250 words, or a shorter exploratory exchange. Let actions and subtext reveal a difference in values.', rows=6),
        ],['The sleuth takes action for a personal, credible reason.','Both romantic leads have independent goals and meaningful choices.','Supporting characters have distinct motives and relationships.'],['sanderson-notes','romance']),
    stage('setting','Make somewhere worth returning to','Design the cosy community in both eras.','time',20,
        'Choose details that affect decisions: a familiar gathering place, who holds power, who knows everyone’s business and what survives between eras. Reveal the setting through what the viewpoint character needs and notices. Separate researched historical facts from inventions and questions still to verify.',
        'Visit the same location in two eras. Describe three physical details, one social rule and one detail that could become a clue.',[
            field('home','The community and its gathering place','Where do people meet? What makes it feel warm? What tensions sit beneath the surface?'),
            field('eras','The same place, then and now','Era/date • sensory details • social expectations • access to rooms or objects • what has changed and what remains.', rows=5),
            field('research','Research notebook','Question • source / link / page • fact learned • invention or uncertainty. Verify dates, technology and language you actually use.'),
        ],['The location shapes access, relationships or conflict.','Readers can distinguish the eras with a few meaningful details.','Historical claims and invented details are distinguishable.'],['sanderson-notes']),
    stage('time','Set the rules of time','Make the impossible dependable enough for a fair mystery.','time',30,
        'Choose a model: a fixed history, a changeable timeline or branching histories. None is universally correct for fiction. Readers need to understand any rule used to resolve the conflict before that resolution. Costs and limitations create hard choices. Track what happens in calendar time separately from the order in which the reader and traveller encounter it.',
        'Test your rules with an object, a memory and an alibi. Then try to break the ending: why can’t the sleuth simply repeat a trip until everything is easy?',[
            field('model','Your time model','Fixed / changeable / branching / another model. What can change? What counts as the same person or timeline?'),
            field('mechanism','Access, limits and costs','Trigger • destination • travel window • who can travel • what travels • cost • return condition • hard limit.'),
            field('memory','Memory, duplicates and objects','Who remembers changes? Can people meet themselves? Where does each important object originate? If a loop has no origin, is that intentional?'),
            field('chronology','Two orders and a knowledge ledger','Calendar date/branch • traveller’s personal sequence • event • who knows it • when the reader learns it. Use one line per event.', rows=6),
            field('stress_test','Try to break the solution','Why no endless retries? Could time travel falsify the culprit’s alibi? Which earlier scene demonstrates the rule that the ending relies on?'),
        ],['The travel mechanism has a stable limitation and a meaningful cost.','Chronology, memory and important objects obey the chosen model.','The resolution uses an established rule and explains why an easy reset cannot solve everything.'],['time-law','sanderson-notes']),
    stage('mystery','Build the crime backwards','Give your reader a puzzle they could solve.','mystery',40,
        'Know what really happened before arranging discoveries. A clue can be noticed, misinterpreted and understood at different times. A red herring should have a truthful explanation. Time travel may complicate an alibi, but the relevant rule must be available to the reader. Let the protagonist deduce and act; a confession can confirm the solution rather than supply everything missing.',
        'Write the culprit’s account first. Create a suspect ledger and a clue ledger. For each decisive clue, record where the reader sees it and how it rules out an alternative.',[
            field('truth','What really happened','Crime • person harmed • culprit • motive • means • opportunity • exact sequence • consequence for the community.', rows=5),
            field('suspects','Suspect ledger','One line per suspect: name • motive • opportunity • alibi and era • secret • why they look guilty • evidence that clears or implicates them.', rows=6),
            field('clues','Clue ledger','ID • visible fact • scene planted • innocent interpretation • true meaning • scene understood • inference it supports. Include at least three useful clues as a starting exercise.', rows=7),
            field('red_herrings','Misleading evidence with honest explanations','Suspicious fact • plausible wrong inference • true explanation • scene resolving it.'),
            field('solution','The chain of deduction','Because [visible evidence], the sleuth rules out [alternative] and tests [hypothesis]. What action proves the answer without introducing a new rule?', rows=5),
        ],['The culprit’s motive, means and opportunity form a coherent account.','The decisive clues reach the reader before the reveal.','Alibis, misleading evidence and the final deduction have explanations consistent with the time rules.'],['mystery','genre']),
    stage('romance','Earn the falling in love','Let solving the case change the relationship.','romance',30,
        'Attraction is more convincing when readers see specific qualities in action. Build trust through choices, vulnerability and repair. A strong obstacle can come from incompatible duties or values; it need not depend on an avoidable misunderstanding. If one person remembers a shared past that the other has not lived, they still need to respect that person’s present choices.',
        'Map six relationship turns. Tie each to an investigation or time travel event so the threads change each other.',[
            field('attraction','Why these two people?','What does each admire? Give an observable moment, an emotional need and a source of friction for each.'),
            field('beats','Relationship turns','First spark • earned respect • voluntary vulnerability • growing intimacy • rupture / hard choice • repair and commitment. Name the connected plot event for each.', rows=6),
            field('obstacle','The obstacle and the cost','What makes being together hard even after an honest conversation? What must each person risk or change?'),
            field('agency','Choice across timelines','What does each person know? How does each choose freely? What practical arrangement makes your HEA/HFN credible across eras?'),
        ],['Mutual attraction and trust are demonstrated through specific actions.','The romantic obstacle grows from the people and the story.','The resolution includes mutual choice, repair where needed and a workable future.'],['romance','genre']),
    stage('comedy','Give the story its comic voice','Find warmth, friction and a well-timed surprise.','comedy',20,
        'Humour can grow from a mismatch between a person’s expectation and reality. Build a recognisable pattern, vary or escalate it, then pay it off. A callback works best when its changed context also reveals character or moves the plot. Leave room for tenderness and grief; the story’s warmth depends on who the joke invites us to laugh with.',
        'Write one small comic beat three ways: a clash of eras, a change in social status and an escalating pattern. Choose the one that fits your narrator.',[
            field('engine','Your comic engine','What predictable habit collides with which unpredictable situation? Whose perspective makes it funny?'),
            field('experiment','Try three versions','Write the setup and turn for each version. Read aloud and cut the explanation after the joke.', rows=6),
            field('callbacks','Setup → escalation → payoff','Track two recurring comic details. Record their scene locations and how the final return changes their meaning.'),
            field('care','Protect the emotional moment','Where should a joke stop? Who is the target of the humour? How do you keep the crime’s consequences and romantic vulnerability meaningful?'),
        ],['The comic turn grows from a clear expectation and this character’s perspective.','A recurring joke changes or escalates instead of merely repeating.','The humour fits the chosen cosy tone and leaves important emotions room.'],['humor']),
    stage('plot','Weave one storyline','Make every turn change more than one thread.','story',35,
        'Use seven turning points as a starting scaffold from the supplied Dan Wells summary, or adapt them freely. Plan the ending and starting state first, then the moment the protagonist begins taking charge. Connect events with “because” and “therefore”. The pressure can be social, emotional or investigative; a cosy story does not require fights or a dead mentor.',
        'For each turn, note what changes in the case, the relationship and the time problem. Include the comic beat only where useful. These turning points can become several scenes each.',[
            field('hook','1 · Opening / hook','Who is the protagonist before change? Show the tone and a reason to care.'),
            field('turn_one','2 · First turn','What disruption and choice entangle the crime, romance and time travel?'),
            field('pressure_one','3 · First pressure','What attempt fails, and what clue or relationship consequence follows?'),
            field('midpoint','4 · Midpoint','What discovery makes the protagonist change strategy and take initiative?'),
            field('pressure_two','5 · Greater pressure','What becomes personally costly? How does the relationship face a real test?'),
            field('turn_two','6 · Final turn','Which already planted clue and established rule enable a new choice?'),
            field('resolution','7 · Resolution','Show the deduction, mutual romantic choice, cost of time travel, restored community and a fitting comic return.'),
        ],['Turning points follow from choices, discoveries and consequences.','Mystery, romance and time travel materially affect each other.','The ending pays off earlier setups and the protagonist’s emotional change.'],['plot-formulas','sanderson-notes']),
    stage('scenes','Turn the outline into scenes','Move from planning to pages.','prose',25,
        'A scene gives a viewpoint character a local desire, resistance and a meaningful change. Quieter reaction scenes can let them absorb a setback, weigh options and decide. Use the Scene desk to build an ordered board from your plot, add or rearrange scenes, and write each scene’s prose. A turning point is not a required chapter length.',
        'Build your scene board below. For each card name the viewpoint and era, the goal and resistance, and the change at its end. Link clues and relationship movement. Then draft the opening without trying to perfect it.',[
            field('strategy','Your drafting plan','What is your next manageable session: scene, time available and a realistic word goal?'),
            field('transitions','Orientation and transitions','How will dates, locations and viewpoint changes help readers follow the jumps?'),
            field('gaps','Questions to discover while drafting','Keep uncertainties here and continue writing when they do not block the next scene.'),
        ],['The scene board covers a beginning, development and ending.','Scenes have a viewpoint, resistance and a change or decision.','Time and location shifts can be followed, and useful clues have places to appear.'],['snowflake','sanderson-notes']),
    stage('voice','Shape the telling','Practise viewpoint, dialogue, rhythm and selective detail.','prose',25,
        'Choose a viewpoint and tense deliberately. Let the narrator’s observations carry the comic voice; allow dialogue to pursue goals beneath the spoken words. Readers need enough context to understand the present action, not every fact in the story bible. Scene, summary, showing and telling all have uses.',
        'Choose a short passage from your Scene desk. Revise for orientation and subtext, then read it aloud for rhythm. Compare before and after. Return your chosen revision to the scene.',[
            field('approach','Your viewpoint and voice','First person or limited third? Whose perspective? Tense? What does this narrator notice or consistently misread?'),
            field('sample','A passage to work on','Paste up to 700 words from a scene. Tell the tutor in your question what you want help with.', rows=10),
            field('decision','Your revision decision','What will you keep or change and why? Put the chosen wording into the Scene desk; this worksheet is not included in the manuscript.'),
        ],['The passage maintains its chosen viewpoint and clear references.','Dialogue or observation reveals character beyond exposition.','Rhythm and detail support the intended emotion and comic timing.'],['sanderson-notes']),
    stage('revision','Revise the whole story','Read for structure first, then continuity, then sentences.','revision',40,
        'Read the assembled manuscript before polishing individual sentences. First check causes, payoffs and character choices; next compare the clue and timeline ledgers to what is actually on the page; finally edit voice, clarity and mechanics. Feedback records a reader’s response, not a verdict. The local tutor reviews the selected worksheet or scene plus labelled planning excerpts; it does not automatically read a whole novel.',
        'Use Manuscript to read from beginning to end. Record exact scene references for each problem. Fix the three largest issues first. Ask a test reader what they expected, where they were confused, when they suspected the culprit and when they believed the romance.',[
            field('development','Pass 1 · Story and emotion','Problem • scene(s) • intended reader experience • proposed change. Check the causal chain, stakes, agency, trust and payoff.', rows=5),
            field('continuity','Pass 2 · Mystery and time audit','Check each clue’s plant and reveal, suspect alibis, dates, memory states, object origins, costs and the final deduction against the actual scenes.', rows=5),
            field('line','Pass 3 · Voice and clarity','List repeated phrases, confusing references, viewpoint slips, pacing issues and jokes that need timing work. Keep intentional voice choices.'),
            field('reader','Reader feedback and your decisions','Reader observation • passage/scene • keep/change/ask • your reason. No outside message is sent by this app.'),
        ],['Structural changes address identified reader effects with scene references.','Clues and time rules have been checked against the manuscript.','Revision choices preserve the intended tone and the author’s voice.'],['sanderson-notes','mystery','time-law']),
    stage('finish','Bring your story together','Make a complete manuscript you can read and share.','revision',20,
        'The manuscript is assembled from the prose in your ordered scene cards. Worksheets, examples and tutor suggestions stay outside it. Review each scene, then complete the final checks here. “Reviewed” records your decision, not a professional certification. You can export a draft at any time; a finished export requires all scenes to be reviewed and these final checks.',
        'Give the story its final title. Read the last scene beside the first. Confirm that the puzzle, relationship and time travel consequences resolve, and finish with the emotional aftertaste you promised.',[
            field('ending','Your ending audit','Where are the crime’s answer, romantic commitment, time travel cost and restored sense of home visible on the page?'),
            field('last_pass','Final read-through notes','Check scene order, missing prose, placeholders, names, dates, punctuation and the opening/closing echo. Record any intentional open threads.'),
            field('reflection','What you learned and what comes next','Name one craft skill that improved and one question for your next story.'),
        ],['Every intended scene has prose, is in the right order and has been reviewed.','The central crime and relationship resolve using established time rules.','The full manuscript has been read for continuity, clarity and the chosen tone.'],['sanderson-course','genre']),
]

STAGE_MAP = {s['id']:s for s in STAGES}
TUTOR_MAP = {t['id']:t for t in TUTORS}
SCENE_CRITERIA = ['The viewpoint, era and immediate goal are clear.', 'Resistance leads to a change, discovery or decision.', 'The scene serves its intended story threads while respecting established facts.']

# One worked fragment per step, offered for learning rather than as manuscript text.
EXAMPLES = {
    'promise':('balance','The theft leads the plot, but every new clue changes how Mara and Leo trust each other. The humour comes from Mara trying to schedule a perfectly spontaneous romance. The final page should feel safe, affectionate and lightly ridiculous.'),
    'theme':('question','Can you build a shared future without controlling it? Early on Mara secretly repeats a conversation to make it go perfectly. At the climax she tells Leo what she knows and lets him choose, even though she cannot undo his answer.'),
    'characters':('sleuth','Mara, archivist, 2026. Wants to save the museum from closure; needs to accept help without managing everyone. Excellent at spotting cataloguing inconsistencies. Treats feelings like missing records she can recover. Investigates because a forged receipt implicates the museum she promised to protect.'),
    'setting':('eras','1926: coal dust in the tea-room window grooves, a bell for summoning staff, a cabinet only the manager may open. 2026: an electric kettle and museum tickets, but the cabinet still has the same warped latch. The unchanged latch matters when someone claims the cabinet locked automatically.'),
    'time':('mechanism','The clock permits three journeys, all to the same Thursday in 1926. Only the traveller and what fits in their coat can cross. Each visit uses one engraved mark. Returning takes the same amount of present-day time, so Leo can notice each absence. These are proposed fictional rules to test, not facts about time travel.'),
    'mystery':('clues','C1: a crescent tea stain on the receipt; planted while Mara wipes the counter in the opening. It initially looks like careless housekeeping. Later the reader learns the matching chipped cup was packed away before the alleged theft, so the receipt’s claimed date cannot be right. A second clue must establish who could have forged it.'),
    'romance':('beats','Respect: Leo lets Mara check the catalogue despite their quarrel. Vulnerability: she admits a trip failed instead of inventing an excuse. Rupture: he learns she used future knowledge to steer him. Repair: she shares the evidence and accepts his independent plan, with no journey left to revise his response.'),
    'comedy':('callbacks','Setup: Mara labels a tin “Emergency biscuits”. Escalation: a suspect mistakes it for evidence and demands a lawyer. Payoff: after the case is solved, Leo relabels it “Ordinary Thursday biscuits”. The changed label gently marks their return to a shared, less controlled life.'),
    'plot':('midpoint','Because the supposedly stolen clock appears in an earlier photograph, Mara stops chasing a thief and starts testing who falsified the date. Asking Leo to help means admitting her first accusation was wrong. The new investigation strategy also becomes the first honest step in repairing their trust.'),
    'scenes':('strategy','Today: 20 minutes on the tea-room opening. Mara wants the catalogue before Leo arrives; a locked cabinet obstructs her; a receipt dated tomorrow changes the problem. Aim for 400 rough words and stop after she decides to test the clock.'),
    'voice':('sample','The clock struck thirteen, which Mara considered rude. She had already been late twelve times that morning.\n\nLeo placed a cup beside the empty cabinet. “Perhaps it is counting your apologies.”\n\nThis is an original comic opening. Its joke grows from the viewpoint character’s preoccupation; your narrator can sound completely different.'),
    'revision':('continuity','Scene 6 uses the chipped cup to date the receipt, but the cup’s disappearance is only mentioned in scene 7. Move the packing-away detail into scene 2 and let the reader see it during the argument. Then check that the culprit still has an opportunity to forge the receipt.'),
    'finish':('ending','Scene 9 resolves the forged receipt through clues C1 and C3. Scene 10 shows Leo choosing a shared future after hearing the whole truth. The clock’s last mark stays spent. The biscuit-tin callback closes the story after the practical consequences are settled.'),
}
for stage_id,(field_id,example) in EXAMPLES.items():
    next(f for f in STAGE_MAP[stage_id]['fields'] if f['id']==field_id)['example']=example

def curriculum():
    return {'version':1,'title':'A little love, a little crime, a wrinkle in time',
            'stages':STAGES,'tutors':TUTORS,'sources':SOURCES,'scene_criteria':SCENE_CRITERIA,
            'principle':'Craft tools, not compulsory formulas. Adapt the workshop to the story you want to tell.'}
