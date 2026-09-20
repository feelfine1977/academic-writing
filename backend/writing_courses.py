"""Original, versioned general-writing courses and their private answer keys.

The linked readings inform the teaching. Their exercises are not reproduced.
Keep published pack content immutable; increment VERSION when changing tasks.
"""
from copy import deepcopy

VERSION = 1
SOURCES = {
    'sanderson': {'id':'sanderson','title':'Brandon Sanderson: Writing Class 2025, Week 1','url':'https://www.brandonsanderson.com/blogs/blog/brandon-sandersons-writing-class-2025-week-1'},
    'mystery': {'id':'mystery','title':'Writing Excuses: Mystery Plotting','url':'https://writingexcuses.com/writing-excuses-6-26-mystery-plotting/'},
    'romance': {'id':'romance','title':'Writing Excuses: Writing Romance','url':'https://writingexcuses.com/writing-excuses-5-31-writing-romance/'},
    'humour': {'id':'humour','title':'Writing Excuses: The Element of Humor','url':'https://writingexcuses.com/11-32-the-element-of-humor/'},
    'grammar': {'id':'grammar','title':'British Council: English grammar','url':'https://learnenglish.britishcouncil.org/free-resources/grammar'},
    'english': {'id':'english','title':'British Council: Writing in English','url':'https://learnenglish.britishcouncil.org/free-resources/writing'},
    'paragraphs': {'id':'paragraphs','title':'Purdue OWL: Paragraphs and paragraphing','url':'https://owl.purdue.edu/owl/general_writing/academic_writing/paragraphs_and_paragraphing/index.html'},
}


def write(title, prompt, criteria, example, explanation):
    return dict(title=title,prompt=prompt,criteria=criteria,format='free_writing',
                example=example,explanation=explanation)


def choose(title, prompt, choices, answer, explanation):
    return dict(title=title,prompt=prompt,criteria=['Choose the option that fits the stated meaning and sentence.'],
                format='gap',choices=choices,expected_values=[answer],explanation=explanation)


def unit(slug, title, goal, lesson, demo, why, sources, tasks):
    return dict(slug=slug,title=title,goal=goal,lesson=lesson,worked_example=demo,
                example_explanation=why,source_ids=sources,tasks=tasks)


CREATIVE = [
    unit('idea','Find a story worth telling','Turn an interesting situation into a character with a difficult choice.',
         'A situation becomes a story when someone wants something, meets resistance and must act. A premise names that engine. Theme is a question the choices explore; it need not be a moral announced by the narrator. Establish what kind of experience readers can expect. These are useful craft tools, not compulsory formulas.',
         'A cautious lighthouse keeper discovers that tomorrow’s letters arrive at low tide. When one predicts her brother’s disappearance, she must trust the smuggler she has been reporting to the police.',
         'The unusual event creates a goal, personal stakes and a costly alliance. The premise raises a question about trust without answering it.',
         ['sanderson'],[
        write('Turn a what-if into a premise','Invent a premise in 2–4 sentences. Include a protagonist, a surprising situation, a concrete goal, an obstacle and the cost of failure. You may use time travel, romance or a cosy mystery.',
              ['Identify a protagonist and a concrete goal.','Connect the unusual situation to an obstacle and meaningful stakes.','Make the premise understandable without outside notes.'],
              'A village baker finds that her oven returns objects to yesterday. When the charity raffle money vanishes, she tries to recover it before the treasurer is blamed. Each trip erases a recipe, and the only witness is the rival baker she refuses to trust.',
              'The device creates both an opportunity and a cost; the investigation gives the protagonist a reason to act.'),
        write('Explore the question beneath the plot','Write a theme question and two opposing but plausible answers. Then invent a difficult choice that could test both answers. Include a one-sentence premise for context.',
              ['Frame theme as an open question.','Give two plausible competing answers.','Test the question through a specific character choice.'],
              'Premise: a baker can revisit yesterday to recover missing charity money. Question: can you protect a community without controlling it? One answer is that preventing every mistake keeps people safe; another is that trust requires letting people choose. She can secretly undo her rival’s confession or let him tell the village what he did.',
              'Both answers have a cost. The choice expresses the theme through action.'),
        write('Make a promise to your reader','For an invented story, describe the intended reader experience in 3–5 sentences. Name the tone, the central question and the sort of payoff you want. Add one concrete opening detail that signals that experience.',
              ['Describe a consistent tone and central story question.','Name an intended payoff.','Use a concrete detail to signal the experience.'],
              'This is a warm mystery with awkward flirtation and a fair solution. Readers will ask who stole the raffle money and whether the rival bakers can work together. The ending will explain the theft and offer a hopeful relationship. In the opening, the detective dusts a croissant for fingerprints while trying to remember her rival’s coffee order.',
              'Tone is demonstrated by an image, and both the mystery and relationship receive a promised payoff.'),
    ]),
    unit('character','Build characters who cause events','Connect desire, fear, contradiction and change to action.',
         'Give a character a visible goal and a reason it matters. A fear or mistaken belief can make a useful strategy fail. Distinctive habits help a character feel particular, but choices drive the plot. An arc can involve change, resistance to change, or holding a value under pressure. Supporting characters need aims of their own.',
         'Mara wants to win the village gardening prize. She insists she needs no help, yet secretly waters her neighbour’s neglected plants. When a drought forces them to share water, her generosity and pride collide.',
         'A contradiction creates behaviour and a relationship problem. The drought forces a choice instead of merely revealing a biography.',
         ['sanderson'],[
        write('Give your protagonist a contradiction','Create a character sketch in 5–7 sentences: visible goal, private fear, useful strength, a behaviour that complicates the goal and a choice under pressure. Show at least one concrete action.',
              ['Connect a goal and fear to behaviour.','Include a useful strength and a complicating contradiction.','Give a specific choice under pressure.'],
              'Elsie wants to keep her bakery open. She fears that accepting help will make her father’s old criticism true. She notices small details and remembers everyone’s preferences. She leaves free bread at her rival’s door but refuses his offer to fix her oven. When a ruined order threatens the charity fair, she must ask him for kitchen space or disappoint the village.',
              'The contradiction affects the plot and creates a decision; the sketch goes beyond a list of traits.'),
        write('Give the other person an agenda','Invent two characters who need one another but want different outcomes. In 4–6 sentences explain each goal, why cooperation is necessary and one boundary each person will defend.',
              ['Give both characters independent goals.','Explain their need to cooperate and a source of friction.','Give each person a meaningful boundary.'],
              'Elsie wants the missing money returned quietly; her rival Theo wants the village to clear his sister’s name publicly. Elsie can revisit yesterday, while Theo knows the fair’s delivery route. They need each other to find the witness. Elsie will not erase someone’s memory without consent. Theo will not use his sister as bait.',
              'The partnership has practical value, disagreement and limits that can shape later choices.'),
        write('Plot change through choices','Write three short beats for one character: an early choice made from fear, a later choice that repeats the mistake with a larger cost, and a final choice showing change or a consciously defended value. Supply a sentence of context.',
              ['Connect all three choices to the same internal conflict.','Escalate the consequence in the middle beat.','Demonstrate the final position through an action.'],
              'Elsie fears depending on other people. First she hides a broken oven and loses a small order. Later she hides a failed time jump, leaving Theo to face a false accusation. Finally she tells the village what she can and cannot do, then asks Theo to lead the witness search.',
              'The final action reverses the earlier pattern and influences the external investigation.'),
    ]),
    unit('world','Choose a viewpoint and consistent world','Make setting, time travel and viewpoint serve the scene.',
         'Setting matters when it changes what characters can do. Choose what the viewpoint character can perceive and know. Close third person usually limits a scene to one person’s experience; omniscient narration is another valid choice. For time travel, define access, limits, costs and what can change. Track event order separately from the order in which readers learn it.',
         'Rule: a station clock permits one ten-minute journey to yesterday, but the traveller returns without the object held in their left hand. Scene detail: Imani pockets the only ticket before touching the clock; a porter notices the empty hand on her return.',
         'The rule creates a visible precaution and a possible clue. Its cost can be checked later.',
         ['sanderson'],[
        write('Make setting do work','Invent a place in 4–6 sentences. Use two sensory details selected by a particular viewpoint character. Include a practical constraint that changes the character’s next action.',
              ['Use a consistent perceiving character.','Choose concrete sensory details.','Make one feature of the setting affect an action.'],
              'Elsie smelt burnt sugar before she saw the locked kitchen door. The fair’s brass band rattled the windowpanes, swallowing her call for help. Through the glass she could see the missing raffle tin on a high shelf. The only open entrance was the serving hatch. She put down her cake and crawled through it.',
              'Sound, smell and access are filtered through Elsie’s immediate problem.'),
        write('Write the rules of the impossible','Define a time-travel mechanism: trigger, reachable time, cost, memory rule and what changes in the present. Then describe one attempted shortcut that those rules prevent. Choose fixed history, a changeable timeline or branching histories and keep it consistent.',
              ['Define access, cost and memory clearly.','Choose a consistent model of change.','Explain a blocked shortcut using an established rule.'],
              'The oven opens a branching path to the previous day when its original bell rings. The traveller stays for ten minutes and loses one remembered recipe on returning. The traveller remembers both branches; everyone else remembers only their own. Objects can cross, but each journey creates a new branch, so repeating a trip cannot repair the abandoned branch. Elsie cannot save her first failed fair simply by trying again.',
              'The consequence follows from branching histories; it is not an exception introduced to stop the protagonist.'),
        write('Keep viewpoint under control','Rewrite this passage in close third person from Nia’s viewpoint: “Nia opened the letter. Across town, Leo hoped she would forgive him. Nia’s hands shook. She did not know that he had hidden the second page.” Preserve the letter and shaking hands. Suggest uncertainty about Leo without entering his mind. Add one sentence explaining your revision.',
              ['Keep narration within Nia’s perceptions and inferences.','Preserve the supplied letter and physical reaction.','Explain how the revision controls access to information.'],
              'Nia opened the letter. Her hands shook as she read Leo’s apology. The final sentence stopped at the edge of the page; she turned it over, searching for the rest. Had he left something out? I replaced access to Leo’s thoughts with details Nia can observe and a question she can ask.',
              'The narrator can suggest concealed information without confirming facts outside Nia’s awareness.'),
    ]),
    unit('plot','Connect plot, clues and consequences','Build a causal outline whose ending has been prepared.',
         'A useful outline connects attempts and consequences: because an action changes the situation, the next choice becomes necessary. Promises, progress and payoff help you check expectations. For a fair mystery, work backwards from the solution, plant discoverable clues and explain misleading evidence. Coincidence may start trouble; the protagonist’s choices should earn its resolution.',
         'Solution: the caretaker hid the trophy to postpone a ceremony. Early clue: fresh polish on an unused cupboard key. Misreading: everyone assumes he wanted the trophy. Payoff: the cupboard also contains the cancellation notices he was afraid to deliver.',
         'The same evidence supports an early suspicion and a later explanation. The answer can be reconstructed from planted details.',
         ['sanderson','mystery'],[
        write('Build a causal outline','Outline five linked beats for a short story: disturbance, first attempt, consequence, harder choice and resolution. Show at least two because/therefore relationships in the explanation; the literal words are optional.',
              ['Make actions cause later developments.','Escalate a problem through an attempted solution.','Resolve the main problem through a character choice.'],
              'The fair’s donation tin disappears. Elsie jumps to yesterday to watch the collection, but forgetting her recipe ruins the cake used to conceal her visit. Theo spots the ruined cake and discovers her secret. She must trust him with the time-travel limit to reconstruct the deliveries. Together they find the tin in a flour crate and confront the organiser who hid it to delay an unsafe event.',
              'The cost of the first attempt forces the partnership that makes the solution possible.'),
        write('Plant a fair clue','Design a miniature mystery in labelled notes: solution, two clues visible before the reveal, one plausible misleading interpretation, and the observation that resolves it. Explain why the sleuth can reach the answer.',
              ['Specify a solution and two relevant planted clues.','Make the misleading interpretation plausible and explainable.','Let the sleuth infer the solution from available information.'],
              'Solution: the treasurer moved the tin into a flour crate to keep it safe from a leaking roof. Clues: wet coins on her desk and flour on the tin’s handle. Misreading: the baker stole it because flour points to the kitchen. Resolving observation: the kitchen flour is brown wholemeal; the white flour came from a delivery crate in the treasurer’s room. The sleuth compares the two before looking in that crate.',
              'The comparison redirects an existing clue rather than supplying an unexplained final revelation.'),
        write('Check the timeline and payoff','Invent a short time-travel plot. List at least four events in chronological order, then the order in which readers discover them. State a time-travel rule and identify an early detail that earns the ending. Explain any apparent contradiction.',
              ['Distinguish event chronology from reveal order.','Keep the events consistent with a stated time rule.','Connect an early detail to an earned ending.'],
              'Rule: history is fixed, and the traveller always participated in it. Chronology: a child drops a key; a masked stranger returns it; twenty years pass; the grown child travels back wearing the mask and returns the key. Reveal order: the adult loses the key, remembers the masked helper, travels, then recognises the child. The mask’s stitched star appears in the memory before the adult repairs it. There is no changed past: the helper was always the adult.',
              'A fixed loop permits the revelation because the remembered event and the later action agree.'),
    ]),
    unit('voice','Write dialogue, romance and humour','Use spoken goals, subtext and comic timing to develop relationships.',
         'Dialogue is action: speakers want something and choose what to reveal. Subtext arises when the spoken topic and the emotional aim differ. Attraction grows through specific attention, friction, vulnerability and choices that change trust. Humour can come from expectation, incongruity or a returning detail. Keep the people and consequences credible within the chosen cosy tone.',
         '“You remembered my umbrella.” “It was blocking the door.” He handed it over, already open. Rain soaked his own shoulders.',
         'The practical excuse and considerate action say different things. The relationship advances without an explicit declaration.',
         ['romance','humour'],[
        write('Let dialogue carry subtext','Write a short exchange between two people discussing a practical problem while avoiding an emotional one. Include an action beat and one sentence identifying what each person wants. Keep speaker changes clear.',
              ['Give each speaker an aim.','Suggest an unspoken emotional concern through words or action.','Make speakers and actions easy to follow.'],
              '“You could leave the spare key,” Mira said. “For the plants.”\nJon set it beside her cup. “They do need watering.”\n“The cactus?”\nHe moved the key closer. “Especially that.”\nMira wants him to return; Jon wants permission to stay part of her life without risking a direct refusal.',
              'The plant discussion provides cover for a relationship negotiation.'),
        write('Change trust through a small choice','Write a brief romantic scene in which practical cooperation changes trust. Give both people agency, include a moment of vulnerability and show the change through a choice rather than a declaration that they are in love.',
              ['Let both people make choices.','Connect vulnerability to a change in trust.','Show the relationship change through concrete action.'],
              'Elsie pushed the broken bell towards Theo. “I told everyone I could fix it.” He opened his toolbox, then paused. “Do you want help or an audience?” “Help.” She handed him the screwdriver she had been gripping all morning. When the bell finally rang, she called the organiser over. “Theo found the fault,” she said. He stayed to help her clean the workbench.',
              'Asking, accepting and publicly crediting help make the shift in trust visible.'),
        write('Set up and return a comic detail','Write a short comic scene with a clear expectation, a surprising but connected turn, and a callback to an earlier detail. Keep the joke compatible with a warm mystery or romance; add one sentence explaining the timing.',
              ['Establish an expectation before changing it.','Connect the comic turn to the situation or character.','Return an earlier detail with a changed meaning.'],
              'The village inspector demanded silence for his reconstruction. Even the kettle, he said, must wait. He arranged the suspects, raised a finger and sat directly on the missing raffle tin. Coins poured across the floor. From the kitchen came a whistle. “The kettle would like to make a statement,” Elsie said. The kettle rule prepares the callback; the inspector’s solemn pose creates the expectation the tin interrupts.',
              'The final line reuses a planted detail and allows the physical discovery to land first.'),
    ]),
    unit('draft','Draft and revise a complete short story','Move from a scene plan to a finished, reviewed story.',
         'A scene usually changes knowledge, options, emotion or commitment. Draft towards that change before polishing every sentence. Revise in passes: first causality and payoff, then character and viewpoint, then clarity, rhythm and grammar. Reader feedback reports an experience; decide which revision serves your intention. Your final story may be flash fiction; completeness depends on a meaningful resolution, not length.',
         'Before: Mina wants to leave before the last train. Turn: she discovers the frightened ticket seller is her younger father. After: she deliberately misses the train to hear him out. Revision question: what established reason makes that costly choice believable?',
         'The scene has a change and a consequence. The revision question targets motivation before sentence polish.',
         ['sanderson'],[
        write('Plan a scene that changes something','Plan one scene in five labelled notes: viewpoint, immediate goal, obstacle, turning choice and changed situation. Include enough story context for a tutor to understand it independently.',
              ['Give a viewpoint character an immediate goal.','Connect an obstacle to a turning choice.','Describe a changed situation at the end.'],
              'Context: Elsie can revisit yesterday but loses one recipe each time. Viewpoint: Elsie. Goal: identify who moved the donation tin. Obstacle: Theo blocks the kitchen door, believing she stole it. Choice: she reveals her ability and admits she cannot risk another jump. Change: he agrees to reconstruct the delivery route with her, so the investigation becomes a partnership.',
              'The scene changes both the method of investigation and the relationship.'),
        write('Write a complete first draft','Write a complete short story, roughly 300–700 words as a manageable starting point. You may bring forward your earlier premise, characters and outline. Give the protagonist a goal, a complication, a consequential choice and a resolution. Include all necessary context in this answer; earlier activities are saved separately. Length is guidance, not an automatic grade.',
              ['Establish a protagonist, goal and intelligible situation.','Make a complication lead to a consequential choice.','Resolve the central story problem and show its effect.'],
              'At six, Ada found tomorrow’s newspaper under her bakery door. At seven, she read that the village fair had lost its donation tin. At eight, she put the paper into her oven. She had learnt last Thursday that burning tomorrow’s news gave her exactly ten minutes in yesterday.\n\nThe kitchen blurred. Yesterday’s cake stood on the table, uniced. Through the serving hatch she saw Ben carrying the tin towards the old storeroom. Ben, who remembered everyone’s birthday. Ben, who had offered to fix her door three times.\n\nShe followed him, ready with an accusation. Then the roof began to drip. He caught the water in his cap, glanced at the coins and shoved the tin into a flour crate.\n\n“Safer there,” he told the caretaker. The caretaker, deaf to anything less urgent than a fire bell, nodded at a broom.\n\nAda felt the pull of the oven. She could grab the tin, return triumphant and explain nothing. Ben would still be the last person seen carrying it. Or she could use her last minute to make sure someone else understood.\n\nShe seized the fire bell.\n\nEvery volunteer arrived, including yesterday’s Ada, who promptly dropped the cake. Ben pointed to the leak, the crate and the coins. Four people saw him lock the tin in the dry cupboard.\n\nBack in today, Ada found a different newspaper. The fair had reached its target. The photograph showed her holding a spectacularly lopsided cake.\n\nBen knocked on the door. “About that bell,” he said.\n\n“I can explain.”\n\n“I hoped so. I’ve been looking forward to hearing you explain a great many things.” He held up his toolbox. “Starting with why you keep asking the postman to deliver a day early.”\n\nAda opened the door wide enough for both of them.\n\n“Tea first,” she said. “Then the impossible bits.”',
              'The discovery changes Ada’s judgement. Her choice secures witnesses rather than leaving Ben under suspicion, and the final invitation changes the relationship. Other plots and lengths can work.'),
        write('Revise and explain your decisions','Paste a revised complete story or a revised self-contained scene from your own draft. Below it add a revision note identifying one change to structure or motivation, one change to the reader’s experience and one sentence-level change. Explain each purpose. If you kept a feature, explain why. You may continue the full project in Fiction Workshop.',
              ['Present a self-contained revised piece.','Explain a structural or motivational decision and its effect.','Explain a reader-experience decision and a sentence-level decision with specific examples.'],
              'Ada followed Ben into the storeroom. He caught the roof’s first drip in his cap, then pushed the donation tin into a flour crate. She lowered the newspaper she had meant to wave in his face. Ten minutes, the oven had promised. One remained. She could take the tin and be a hero; she could leave him looking like a thief. She reached for the fire bell.\n\nRevision note: I made the remaining minute explicit so her choice has pressure. I kept the cap catching the drip because a small considerate act changes how Ada sees Ben. I replaced “made the decision to ring” with “reached for” to keep the last moment immediate.',
              'The revision note names changes and purposes instead of merely claiming the writing improved.'),
    ]),
]


GRAMMAR = [
    unit('sentences','Sentence structure and agreement','Find the main clause and match subjects with verbs.',
         'A standard complete declarative sentence needs a main clause: a subject and a finite verb, with any required complement. A dependent clause beginning with because or although cannot usually stand alone in formal prose. The verb agrees with the subject, not a nearby noun. Deliberate fragments can work in dialogue or creative prose; distinguish that choice from an accidental fragment.',
         'The box of old postcards is under the stairs. Although the cards are faded, their dates are clear.',
         'Box controls is; cards controls are. Although introduces a dependent clause joined to a main clause.',
         ['grammar'],[
        choose('Find the subject','Choose the verb: The list of missing keys ___ on the desk.',['are','is','be'],'is','The singular subject list takes is; keys belongs to the of phrase.'),
        choose('Finish the dependent clause','Which option is a complete sentence in standard written English?',['Because the last bus was late.','Because the last bus was late, we walked home.','The last bus because was late.'],'Because the last bus was late, we walked home.','The because clause has a main clause: we walked home.'),
        write('Repair a short message','Edit this message for sentence completeness and agreement, keeping its meaning: “The box of tickets are in the office. Because the doors open at six. Every volunteer need a badge.” Explain two repairs.',
              ['Use agreement appropriate to box and every volunteer.','Repair the dependent-clause fragment without losing the opening time.','Explain two grammatical repairs.'],
              'The box of tickets is in the office. The doors open at six. Every volunteer needs a badge. I used is because box is singular, and needs because every volunteer is singular. I made the opening time a main clause because the original because clause lacked one.',
              'A separate opening-time sentence keeps the supplied facts without inventing a causal relationship.'),
    ]),
    unit('tense','Tense, aspect and time','Show when events happen and how they relate.',
         'Choose tense and aspect for the timeline you mean. The past simple locates a completed event; the past continuous can present an event in progress. The present perfect connects an earlier event or period to now, while the past perfect places an event before another past reference point. Time words and context guide the choice. A tense shift is useful when the time perspective changes.',
         'I was checking the timetable when the lights went out. The last train had already left.',
         'Was checking gives background in progress; went out gives the interrupting event; had left places the departure earlier.',
         ['grammar'],[
        choose('Place a finished event','Choose the form: Yesterday, Noor ___ the lost parcel to the station.',['has taken','took','takes'],'took','Yesterday fixes the event in a finished past time, so the past simple fits.'),
        choose('Mark the earlier past','Choose the past perfect form to make the earlier action explicit: By the time we reached the cinema, the film ___.',['has started','had started','is starting'],'had started','Had started explicitly places the start before the past arrival.'),
        write('Tell the sequence clearly','Write 3–5 sentences using these facts: at 8 pm yesterday you were cooking; the phone rang; your friend had missed the last bus; you offered a lift. Use tense and aspect to show the background, interruption and earlier event. Explain one choice.',
              ['Preserve the supplied event sequence.','Distinguish background action, interruption and earlier past.','Explain one tense or aspect choice.'],
              'At eight yesterday evening, I was cooking when the phone rang. My friend had missed the last bus and needed a lift. I offered to collect her. I used had missed because missing the bus happened before the call.',
              'The forms make the time relationships clear without putting every verb into the same tense.'),
    ]),
    unit('nouns','Articles, nouns and quantity','Signal what is known, new or countable.',
         'Use a or an to introduce one nonspecific singular countable item; the points to something identifiable in context. A/an follows sound: an hour, a university. Plural and uncountable nouns can take no article when used generally. Countability depends on meaning: coffee can mean a substance or a serving. Quantity words must fit the noun and intended amount.',
         'I bought a map. The map shows the old station. I also asked for some advice and two bottles of water.',
         'A introduces the map; the refers back to it. Advice is normally uncountable; bottles provides a countable unit.',
         ['grammar'],[
        choose('Choose by sound','Choose the article: The repair took ___ hour.',['a','an','no article'],'an','Hour begins with a vowel sound; the h is silent.'),
        choose('Handle uncountable nouns','Choose the natural form: Could you give me ___ about the route?',['an advice','some advice','several advices'],'some advice','Advice is normally uncountable in this meaning. Some advice or a piece of advice works.'),
        write('Introduce and refer back','Edit this message in ordinary written English: “I found wallet near station entrance we use every day. A wallet contains two ticket and an information about a hotel.” Make the wallet new on first mention and identifiable on second mention. Explain an article or quantity choice.',
              ['Introduce the wallet and refer back consistently.','Use natural countable and uncountable noun forms.','Preserve the situation and explain one choice.'],
              'I found a wallet near the station entrance we use every day. The wallet contains two tickets and some information about a hotel. I used the on the second mention because the reader now knows which wallet I mean.',
              'The identifying phrase supports the station entrance; tickets is plural and information is uncountable here.'),
    ]),
    unit('reference','Pronouns and relative clauses','Help the reader identify people and things accurately.',
         'A pronoun needs a recoverable referent: readers should be able to tell who or what it means. Repeat a name when two plausible referents compete. Relative clauses identify a noun or add information about it. Commas around a non-defining relative clause change its job; compare the students who passed with the students, who passed. Singular they is a valid choice.',
         'Lena told Priya that Priya’s train was cancelled. The station café, which stays open late, offered Priya a seat.',
         'Repeating Priya removes an ambiguity. The comma-marked clause adds information about the identified café.',
         ['grammar'],[
        choose('Make the owner explicit','The mug belongs to Omar. Which sentence makes that ownership unambiguous?',['Omar told Felix that his mug was broken.','Omar told Felix that Omar’s mug was broken.','He told him that his mug was broken.'],'Omar told Felix that Omar’s mug was broken.','Repeating Omar names the owner instead of asking the reader to choose between two possible referents.'),
        choose('Add non-defining information','Choose the relative pronoun: Our only village bakery, ___ opens at six, is next to the bridge.',['that','which','what'],'which','Which introduces the non-defining clause about the already identified bakery; that is not used in this comma-marked construction.'),
        write('Clarify the reference','Edit these sentences to express the stated meaning: “Maya handed Ruth her notebook. The guide which greeted them was smiling.” The notebook belongs to Maya; the guide is a person. Explain how your wording helps the reader. A valid who or that clause is acceptable.',
              ['Make Maya’s ownership unambiguous.','Use an appropriate relative construction for the person.','Explain the reference choices.'],
              'Maya handed her own notebook to Ruth. The guide who greeted them was smiling. Her own makes Maya the owner in this construction, and who refers to the person serving as guide.',
              'The repair clarifies the intended meaning instead of treating every pronoun as an error.'),
    ]),
    unit('clauses','Connect clauses and punctuate meaning','Choose conjunctions and sentence boundaries that express the relationship.',
         'Because introduces a reason; although introduces a concession; if introduces a condition. A conjunction does more than join words: it tells readers how ideas relate. Avoid joining two independent clauses with only a comma in standard edited prose. Use a full stop, a semicolon or an appropriate conjunction. However is a linking adverb, not a coordinating conjunction.',
         'Although the shop was closed, a light was on upstairs. We knocked; however, nobody answered.',
         'Although marks the unexpected contrast. The semicolon separates complete clauses before however.',
         ['grammar'],[
        choose('Express a concession','Choose the connector that explicitly marks concession: ___ the rain was heavy, the outdoor concert continued.',['Although','Because','Unless'],'Although','Although marks the concert continuing despite a condition that might have stopped it.'),
        choose('Check a sentence boundary','Choose the conventional punctuation for two independent clauses linked with however.',['The door was locked, however, a window was open.','The door was locked; however, a window was open.','The door was locked however a window was open.'],'The door was locked; however, a window was open.','A semicolon joins the independent clauses; a comma follows the linking adverb however.'),
        write('Repair connections without changing meaning','Revise this passage in standard edited prose: “Although the shop was closed, but the owner let us in. We had forgotten our tickets, however, she found our names on the list.” Keep both contrasts and explain your punctuation.',
              ['Repair the although/but construction.','Use a valid boundary around however or a suitable alternative.','Preserve both contrasts and explain the repair.'],
              'Although the shop was closed, the owner let us in. We had forgotten our tickets; however, she found our names on the list. I removed but because although already makes the first clause dependent. I used a semicolon before however to separate the two complete clauses.',
              'The grammatical repair retains the original relationships; two sentences around however would also work.'),
    ]),
    unit('editing','Modals, conditions and an editing routine','Express certainty and hypothetical outcomes, then edit in deliberate passes.',
         'Modal verbs express meanings such as possibility, necessity and obligation. After must, might and can, use the base verb without to. Conditional forms depend on whether a situation is open, hypothetical or counterfactual. If I had known, I would have called describes an unreal past. Edit first for intended time and meaning, then clauses and agreement, then articles, punctuation and spelling.',
         'The parcel might arrive today. If I had known the office was closed, I would have collected it yesterday.',
         'Might leaves the arrival uncertain. The past counterfactual imagines a different earlier choice.',
         ['grammar'],[
        choose('Use a modal construction','Choose the grammatical form: Visitors must ___ at reception.',['to sign in','sign in','signs in'],'sign in','Must is followed by the base verb without to.'),
        choose('Imagine a different past','Choose the standard past counterfactual: If I had seen your message, I ___ you.',['will call','would have called','would call'],'would have called','Would have called pairs with had seen to imagine an unreal past result.'),
        write('Edit and explain a full message','Edit this message for standard English while keeping the situation: “Yesterday I have missed the bus. My friend which lives nearby offer me an advice: I should to book a taxi. If I had checked the timetable, I would catch the earlier bus. The driver were kind, he returned my wallet.” Explain at least three repairs covering time, sentence structure and another grammar point.',
              ['Keep the missed bus, advice, hypothetical earlier bus and returned wallet.','Use appropriate tense, conditional, modal, noun and agreement forms.','Repair the sentence boundary and explain three distinct repairs.'],
              'Yesterday I missed the bus. My friend, who lives nearby, offered me some advice: I should book a taxi. If I had checked the timetable, I would have caught the earlier bus. The driver was kind; he returned my wallet.\n\nI used the past simple with yesterday and the past counterfactual for the imagined earlier bus. Should takes book without to, and advice is uncountable here. I changed were to was for driver and used a semicolon between the final complete clauses.',
              'The editing pass addresses time and meaning before local forms. Two final sentences would also be valid.'),
    ]),
]


ENGLISH = [
    unit('audience','Purpose, reader and register','Choose wording for a real communicative situation.',
         'Before drafting, decide who will read the text, what they need and what you want them to understand or do. Register is the degree and kind of formality appropriate to the relationship and setting. Plain, direct English can also be polite. A request usually works better when it names the action, provides relevant context and gives a usable time frame.',
         'To a colleague: Could you send the room number by Thursday? I need it for the invitations. To a friend: Which room did we book? I’m sending the invites on Thursday.',
         'Both messages request the same information. The relationship changes the wording, not the facts.',
         ['english'],[
        choose('Choose a usable request','You are writing to an unfamiliar course organiser. You need the start time for tomorrow’s workshop. Which message is clearest and suitably polite?',['Send details immediately.','Could you confirm what time tomorrow’s workshop starts?','I am writing about the aforementioned matter.'],'Could you confirm what time tomorrow’s workshop starts?','The message names the information, event and time without demanding or hiding the request.'),
        write('Write for two readers','Write two messages asking to borrow a bicycle for Saturday: one to a close friend and one to a neighbour you barely know. Keep the request and date consistent; make the register fit each relationship.',
              ['Make the same request and date clear in both versions.','Adjust wording to the two relationships.','Give the reader room to respond or decline.'],
              'Friend: Hi Jo! Could I borrow your bike on Saturday? No worries if you need it.\nNeighbour: Hello Ms Reed, would it be possible to borrow your bicycle on Saturday? I understand if that is inconvenient. Thank you for considering it.',
              'Both versions leave the choice with the recipient while making the request explicit.'),
        write('Remove formality that hides the purpose','Rewrite this email in clear, polite English: “I am writing with regard to the matter of the arrangements previously alluded to. It would be appreciated if clarification could be provided in due course.” Context: you booked a library room for Friday and need to know by Wednesday whether it has a projector. Explain one change.',
              ['Name the Friday room booking and projector question.','Make the Wednesday response time clear.','Use polite direct wording and explain one choice.'],
              'Hello, could you confirm by Wednesday whether the room I booked for Friday has a projector? I need to prepare the presentation. Thank you. I replaced the vague request for clarification with the specific equipment question and deadline.',
              'The reader can identify the action without decoding abstract references.'),
    ]),
    unit('paragraph','Plan and develop a paragraph','Give a paragraph a purpose and order its supporting details.',
         'A paragraph should develop a recognisable purpose. Choose what the reader needs first, then support it with useful details or examples. Arrange those details by a meaningful relationship, such as sequence, comparison or reason. A topic sentence can help; it need not always come first, and fiction may use shorter paragraphs for dialogue or emphasis. Remove a detail when it distracts from the paragraph’s job.',
         'The riverside path is the easiest route to the library. It has no steps, follows one bank and ends beside the entrance. On rainy days, take the paved branch after the bridge because the grass section floods.',
         'The recommendation is developed by practical reasons and a relevant condition. Each sentence helps the same reader decision.',
         ['paragraphs','english'],[
        choose('Find the useful supporting detail','A paragraph explains how to reach the new library by bus. Which detail best supports its purpose?',['The library’s architect also designed a hotel.','Get off at Market Square and walk two minutes east.','I have always liked novels.'],'Get off at Market Square and walk two minutes east.','The stop and walking direction directly help the reader reach the library.'),
        write('Plan before you draft','Plan a paragraph recommending a quiet place to write. State its purpose, the reader you have in mind, a main recommendation and three supporting details in a useful order. Explain that order in one sentence.',
              ['Identify reader and paragraph purpose.','Support a clear recommendation with three relevant details.','Explain a useful order.'],
              'Reader: a friend who writes before work. Purpose: help her choose a reliable morning writing spot. Recommendation: the upstairs library room. Details: it opens at seven; the upstairs area is silent; a desk near the stairs has a power socket. Order: I move from whether she can get in, to whether she can concentrate, to where she can work.',
              'The detail order follows the reader’s practical decisions.'),
        write('Develop one connected paragraph','Write a paragraph recommending a weekend activity to a friend. Include a clear recommendation, two concrete supporting details and a relevant condition or limitation. End in a way that helps your friend decide. You may invent the scenario.',
              ['Develop one clear recommendation.','Use concrete details and a relevant limitation.','Connect the sentences into a useful reader decision.'],
              'Try the Saturday pottery class at the community centre. The teacher demonstrates each step, and the fee includes clay and firing, so you do not need equipment. It lasts three hours, which may be too long if you only have the morning free. If you can spare the time, it is a relaxed way to learn something together.',
              'The limitation helps the friend judge fit; it does not derail the recommendation.'),
    ]),
    unit('words','Choose natural, precise words','Practise collocations, concrete verbs and reliable word choices.',
         'Words have preferred partners: make a decision, take a break, interested in. Learn a useful phrase in context rather than memorising isolated synonyms. Check a learner’s dictionary for meaning, grammar pattern and examples when unsure. Prefer the word that preserves your meaning and suits your reader; a longer or rarer word is not automatically better. Regional alternatives can both be correct.',
         'Vague: We did the necessary things for the trip. Precise: We booked the train and packed the tickets. Useful phrase: make arrangements for a trip.',
         'The revision names actions. The phrase can help when a general description is actually what the reader needs.',
         ['english','grammar'],[
        choose('Use a natural collocation','Choose the verb: We need to ___ a decision before noon.',['do','make','perform'],'make','Make a decision is the conventional collocation in this context.'),
        write('Replace vague words with useful detail','Rewrite “The event was very good and the people did a lot of nice things.” Context: volunteers served hot soup, repaired twelve bicycles and helped neighbours meet one another. Write two clear sentences without exaggerating. Explain one word choice.',
              ['Use specific actions from the supplied context.','Preserve the facts without exaggeration.','Explain a word choice in relation to meaning or reader.'],
              'Volunteers served hot soup and repaired twelve bicycles. The event also gave neighbours a chance to meet. I used repaired because it names what the volunteers did, while “did nice things” leaves the action unclear.',
              'Concrete verbs and the supplied number communicate more than a generic positive judgement.'),
        write('Build a phrase notebook entry','Create entries for three useful English phrases: “look forward to”, “take part in” and “be responsible for”. For each, explain its meaning in plain English and write your own complete sentence in a realistic context. Use a noun or -ing form where the phrase requires it.',
              ['Explain all three phrases accurately.','Use each phrase in a meaningful complete sentence.','Use suitable complements and consistent context.'],
              'Look forward to: feel pleased about something that will happen. I look forward to meeting the other writers.\nTake part in: participate. I plan to take part in the library workshop.\nBe responsible for: have a duty to manage or do something. I am responsible for bringing the notebooks.',
              'Meeting and bringing are -ing complements; the phrases are practised in usable situations.'),
    ]),
    unit('flow','Link ideas and guide the reader','Use relationships, reference and information order to create flow.',
         'Flow comes from ideas that connect, not from adding a transition to every sentence. Introduce a person or topic before using a pronoun for it. Link familiar information to the next new point. Choose a connector only when its relationship is true: because gives a reason, however a contrast, and for example an illustration. Repeating a clear key noun can be better than an uncertain synonym.',
         'The bookshop has opened a reading room. The room seats twelve people, so large groups need to book ahead. Smaller groups can usually drop in.',
         'The room refers back to a named place. The seating limit motivates the booking advice, and the final sentence develops the group-size contrast.',
         ['paragraphs','english'],[
        choose('Link the actual relationship','The second sentence contrasts with the first. Choose the connector: The hotel is close to the station. ___, its rooms are expensive.',['Therefore','However','For example'],'However','However signals the contrast between convenient location and high price.'),
        write('Repair a confusing message','Revise this message so a visitor can follow it: “It is beside the park. They close at five. The museum has a café. This is why you should go early.” Known facts: the museum is beside the park; the museum and café close at five; arriving early leaves time for both. Keep all these facts.',
              ['Introduce places before relying on pronouns.','Make the closing time apply clearly to both places.','Connect the early arrival advice to its reason.'],
              'The museum is beside the park and has a café. Both close at five, so arrive early if you want time for the exhibits and a café visit.',
              'Named places make both recoverable, and the closing time supplies the reason for the advice.'),
        write('Move between two paragraphs','Write two short paragraphs explaining a change of venue for a writing group. Facts: the old café closes on Mondays; the library has offered a Monday room with eight seats; twelve people usually attend; the group must decide whether to split into two sessions. Make the second paragraph develop the unresolved issue in the first.',
              ['Explain the change using the supplied facts.','Make the capacity problem and decision clear.','Connect the paragraphs through a specific continuing issue.'],
              'Our usual café now closes on Mondays, so the library has offered us a room for our writing group. The room is available that evening, but it seats only eight people.\n\nWith twelve regular members, we cannot all meet there at once. We need to decide whether two sessions would work for everyone before confirming the room.',
              'The second paragraph picks up the seating limit and explains the choice it creates.'),
    ]),
    unit('forms','Emails, explanations and reviews','Adapt structure to three useful kinds of writing.',
         'Different texts answer different reader questions. An email often needs a clear purpose and requested next step. Instructions need an achievable order, necessary conditions and a way to recognise completion. A review offers a judgement supported by specific experience and tells readers who might benefit. Choose headings, lists or paragraphs when they make the job easier.',
         'Instruction: Save your draft before closing the editor. Choose Save version, then check that the new version appears in the list. Review: The quiet room suited solo work, but the small tables were awkward for groups.',
         'The instruction includes a verification step. The review connects a concrete feature to a particular user’s needs.',
         ['english'],[
        write('Write an email that gets an answer','Write a polite email to a workshop organiser. You booked for 14 October, now need 21 October, and want to know whether the booking can be transferred and whether there is a fee. Include a subject line and a clear next step. Do not assume the change is already agreed.',
              ['Include both dates and the requested transfer.','Ask about availability and any fee without assuming approval.','Use an appropriate subject, tone and next step.'],
              'Subject: Request to move workshop booking to 21 October\n\nHello, I have a booking for 14 October. Would it be possible to transfer it to 21 October? Please let me know whether a place is available and whether a transfer fee applies. Thank you for your help.\nBest wishes, Alex',
              'The email states the desired action and asks for the missing information.'),
        write('Explain a process someone can follow','Write instructions for borrowing a book from a small community library. Facts: find the book; take it and your membership card to the desk; the volunteer records the loan; check the return date on the slip; return it by that date. Use an ordered list or a clear paragraph. Include a completion check.',
              ['Present all necessary steps in a usable order.','Name the membership card and return deadline.','Tell the reader how to verify the loan information.'],
              '1. Find the book you want to borrow.\n2. Take it and your membership card to the desk.\n3. Wait while the volunteer records the loan.\n4. Check the return date on the slip before leaving.\n5. Bring the book back by that date.',
              'The return-slip check makes the process usable without inventing a renewal policy.'),
        write('Write a balanced reader-focused review','Write a short review of a fictional café for someone choosing a writing spot. Facts: comfortable chairs, reliable Wi-Fi, loud music after 5 pm and only two power sockets. Give a clear overall judgement, support it with details and say who it suits.',
              ['Give a clear judgement supported by the supplied features.','Explain both an advantage and a limitation.','Identify the kind of visitor or visit it suits.'],
              'This café works well for a short afternoon writing session. The chairs are comfortable and the Wi-Fi is reliable, but there are only two power sockets, so bring a charged laptop. Loud music starts after five. I would choose it for daytime solo work rather than an evening session that needs quiet.',
              'The recommendation depends on the visitor’s needs instead of calling every feature universally good or bad.'),
    ]),
    unit('revision','Draft, revise and finish in English','Complete a useful text and explain your editorial decisions.',
         'Plan for a reader, draft the full message and then revise from large decisions to small ones. Check whether the purpose and necessary details are present before polishing individual words. Read aloud for missing connections, then check reference, tense, articles and punctuation. Feedback is a proposal to evaluate. Record what you changed and why so the lesson transfers to your next piece.',
         'Before: It has been decided that a change will happen soon. After: Our writing group will meet at the library from 3 November. Please confirm by Friday whether the new room works for you.',
         'The revision names the group, change, date and requested action. Concision follows from resolving vague meaning.',
         ['english','paragraphs'],[
        write('Plan a practical piece','Plan a short English text you actually want to write: an email, explanation, review or story introduction. State reader, purpose, desired response, four necessary details and a useful order. Invent a scenario if needed.',
              ['Identify a reader, purpose and desired response.','List four details relevant to that purpose.','Choose an order that helps the reader.'],
              'Text: email inviting neighbours to a book swap. Reader: people in our building. Purpose: explain the event and invite participation. Response: tell me whether they will come. Details: Saturday 10 October, 2 pm, shared garden, bring up to three books. Order: invitation, time and place, what to bring, request for a reply.',
              'The plan makes the practical information and requested action available before drafting.'),
        write('Draft the complete text','Write the English text you planned, or invent a new practical scenario. Include a one-sentence brief identifying reader and purpose, followed by the complete text. Aim for about 150–300 words if that helps; use the length the task needs. Earlier answers are separate, so include the necessary context here.',
              ['Make the reader and purpose clear in a separate brief.','Deliver a complete text with necessary context and details.','Use structure, tone and wording appropriate to the purpose.'],
              'Brief: an email inviting neighbours to a small book swap and asking who will attend.\n\nSubject: Garden book swap on 10 October\n\nHello everyone,\n\nWould you like to swap a few books on Saturday 10 October? We will meet in the shared garden at 2 pm. Bring up to three books you are happy to pass on. You are also welcome to come without books and join the conversation.\n\nWe will put the books on the large table, leave time to browse and then let everyone choose something to take home. Please add a note if a book has loose pages or another problem, so the next reader knows what to expect. Children are welcome with an adult.\n\nPlease reply by Thursday to let me know whether you plan to come. That will help me arrange enough chairs. If it rains, I will send an update about postponing the swap.\n\nI hope to see you there.\nAlex',
              'The invitation supplies logistics, participation guidance and a response request in a reader-friendly order.'),
        write('Finish with an editing note','Submit a revised complete text, with a brief naming its reader and purpose. Add an editing note that quotes two specific before/after changes from your own draft and explains their effects. Check purpose, organisation, word choice and grammar. You can use an earlier draft from Saved answers.',
              ['Provide a complete revised text suited to its stated reader and purpose.','Quote two before/after changes in a separate editing note.','Explain the changes in terms of meaning, reader needs or language.'],
              'Brief: a message asking my writing group to confirm a new meeting room.\n\nHello everyone, the café will be closed next Monday. We can meet in the library’s first-floor room at 6 pm instead. There are eight seats, so please reply by Friday if you plan to attend. If more than eight people want to come, I will ask the group about a second session before confirming the room.\n\nEditing note: I changed “It is unavailable” to “the café will be closed next Monday” to name the place and date. I changed “please make a response” to “please reply by Friday” for a natural verb and a usable deadline.',
              'The final version resolves the practical question while the editing note explains two transferable decisions.'),
    ]),
]


COURSES = [
    dict(id='creative-writing',pack_id='WL-CREATIVE',title='Creative Writing',kind='writing',domain='creative',skill='S11',
         goal='Develop ideas, characters and scenes, then draft and revise a complete short story.',
         introduction='Begin with a small idea and build it into a story. You can practise with time travel, romance and cosy mystery, or choose another genre. Keep your favourite answers for your Fiction Workshop project.',
         outcome='A complete short story and a revision note explaining your craft choices.',
         workshop_url='#fiction',modules=CREATIVE),
    dict(id='grammar',pack_id='WL-GRAMMAR',title='Grammar',kind='writing',domain='grammar',skill='S12',
         goal='Understand sentence patterns, practise accurate choices and edit your own English with confidence.',
         introduction='Work from sentence basics through tense, articles, reference and punctuation to a complete editing task. Each module combines two checked choices with an application in your own words. Valid British and American forms are welcome.',
         outcome='An edited message with explanations you can reuse when checking your writing.',modules=GRAMMAR),
    dict(id='writing-in-english',pack_id='WL-ENGLISH',title='Writing in English',kind='writing',domain='english',skill='S13',
         goal='Write clear, natural English for a reader: plan, develop, connect, draft and revise.',
         introduction='Practise communication beyond individual grammar rules. Move from audience and paragraphs to natural word choices, emails, explanations and reviews. Finish a text for a real purpose. Start wherever useful; these modules do not assign a CEFR level.',
         outcome='A complete practical text and an editing note showing how you improved it.',modules=ENGLISH),
]


def curriculum_specs():
    result=[]
    for course in COURSES:
        item={k:deepcopy(v) for k,v in course.items() if k not in ('modules','skill','pack_id','domain')}
        item['modules']=[]
        for index,mod in enumerate(course['modules'],1):
            item['modules'].append({k:deepcopy(v) for k,v in mod.items() if k not in ('tasks','slug','source_ids')} |
                                   {'id':f'{course["id"]}-{mod["slug"]}', 'position':index,
                                    'readings':[deepcopy(SOURCES[s]) for s in mod['source_ids']]})
        result.append(item)
    return result


def packs():
    for course in COURSES:
        exercises=[];answers=[]
        for mi,mod in enumerate(course['modules'],1):
            for ti,task in enumerate(mod['tasks'],1):
                id=f'{course["pack_id"]}-M{mi:02}-T{ti:02}'
                closed=task['format']=='gap'
                exercises.append({k:deepcopy(v) for k,v in task.items() if k not in ('example','explanation','expected_values')} |
                    dict(id=id,module_id=f'{course["id"]}-{mod["slug"]}',course_domain=course['domain'],
                         topic_id=course['id'],topic_title=course['title'],topic_goal=course['goal'],family=mod['title'],
                         skill_ids=[course['skill']],source_ids=mod['source_ids'],
                         level='guided' if closed else 'fresh_prose',difficulty='foundation' if closed else 'developing',
                         learning_objective=mod['goal'],teaching_note=mod['lesson'],tutor_guidance=mod['lesson'],
                         hints=[mod['lesson'],'Check each criterion against the actual words you wrote.'],
                         response_contract={'exact_match_allowed':closed,'value_count':1} if closed else {'exact_match_allowed':False}))
                answers.append(dict(id=id,answer_type='ordered_gap_values' if closed else 'rubric',
                                    expected_values=task.get('expected_values',[]),example=task.get('example'),
                                    explanation=task['explanation'],criteria=task['criteria']))
        used=sorted({s for e in exercises for s in e['source_ids']})
        yield (dict(schema='awl.exercise-pack.v1',pack_id=course['pack_id'],version=VERSION,title=course['title'],
                    origin='assistant_authored',sources=[deepcopy(SOURCES[s]) for s in used],exercises=exercises),
               dict(schema='awl.answer-key.v1',pack_id=course['pack_id'],pack_version=VERSION,
                    origin='assistant_authored',answers=answers))


def teaching_support(exercise):
    """A separate scenario demonstrates the module principle, never the task answer."""
    for course in COURSES:
        for mod in course['modules']:
            id=f'{course["id"]}-{mod["slug"]}'
            if exercise.get('module_id')!=id or not exercise['key'].startswith(course['pack_id']+'@'):
                continue
            steps=['Read the task and decide what your reader needs.',
                   'Use the module lesson to try the requested operation.',
                   'Compare your answer with every criterion; revise the part that needs attention.']
            output=('Choose one of the supplied options, then check your answer.' if exercise['format']=='gap' else
                    'Write the response requested in the task. Include its necessary context; earlier saved activities are separate.')
            example=dict(id=id+'-demo',subject=mod['title'],task='Notice how this separate example applies the lesson.',
                         answer=mod['worked_example'],moves=[mod['example_explanation']],transfer=mod['goal'],
                         provenance='Original teaching example. This illustrates a principle; it is not the answer to your activity.')
            help=dict(version=VERSION,kind=exercise['format'],output=output,steps=steps,terms=[],
                      hints=[{'title':'The principle','text':mod['lesson']},{'title':'Your task','text':output},
                             {'title':'Review','text':'Check: '+'; '.join(exercise['criteria'])}])
            return dict(version=VERSION,scope=course['title'],exercise_key=exercise['key'],tailored=True,
                        example=example,task_help=help,bridge_ideas=[],output_note=output)
    return None
