from copy import deepcopy

import pytest

from backend.coaching_context import model_packet, VERSION


def frozen():
    return {
        'writer_question':'Does the first connection work? I have not written the next move yet.',
        'text_to_discuss':'Records show visits []. [Explain meaning here.] These observations can inform the next question.',
        'selected_text':'Records show visits [].',
        'submitted_scope':'selected passage',
        'surrounding_draft':{'before':'An earlier sentence.', 'after':'[Next idea still to write.]'},
        'stage':'connect', 'persona':'narrative', 'allow_suggestions':False,
        'outline_focus':{
            'selected':{'id':'evidence','title':'Introduce evidence','points':['Name the observations.'],
                        'bridge_question':'How might they help?','boundary':'Do not imply a measured benefit.'},
            'before':{'id':'context','title':'Context','purpose':'Explain the whole setting.','points':['Previous planned content.']},
            'after':{'id':'problem','title':'Problem','purpose':'Explain the unresolved problem.',
                     'points':['A later requirement.'],'bridge_question':'A future connecting question.'},
        },
        'current_brief':{
            'Purpose':'Explain every part of the introduction.',
            'Main message':'Reach the final research contribution.',
            'Writing outline':'All future moves and their requirements.',
            'Section writing plan':'A duplicate full outline.',
            'Supervisor comments and editing consequences':'A duplicate meeting interpretation.',
            'Private coaching preferences':'General preferences plus possible later-section reminders.',
            'Reasoning and decisions':'Decisions about future sections.',
            'Source mapping':'Later-source ideas.',
            'Next writing action':'The following move, not the current requested check.',
            'Writing intention':'Connect the observations to a question.',
            'Scope and boundaries':'Do not claim that visits establish learning.',
            'An unknown later field':'Must not leak silently into the selected-move requirements.',
        },
        'grounding':{
            'available':True,
            'coaching_records':[{'id':'connection','status':'active','instruction':'Make a needed relation understandable.',
                'not_applicable_when':'The relationship is already expressed.',
                'evidence':[{'source_id':'discussion','quote':'Keep the words that already work.', 'locator':'P0002', 'hash':'exact-source-hash'}]}],
            'general_bases':[{'id':'author-question','instruction':'Answer the current question.'}],
            'conflicts':[], 'notices':['These are recorded interpretations, not independent source verification.'],
        },
        'context_limits':{'shortened_fields':[], 'whole_section_supplied':False},
    }


def test_selected_move_packet_retains_exact_draft_question_and_source_records():
    original = frozen(); before = deepcopy(original)
    packet = model_packet(original)
    for field in ('writer_question','text_to_discuss','selected_text','surrounding_draft','grounding','context_limits'):
        assert packet[field] == before[field]
    assert packet['outline_focus']['selected'] == before['outline_focus']['selected']
    assert packet['grounding']['coaching_records'][0]['not_applicable_when'] == 'The relationship is already expressed.'
    assert '[Explain meaning here.]' in packet['text_to_discuss'] and '[]' in packet['text_to_discuss']
    assert original == before
    packet['grounding']['coaching_records'][0]['evidence'][0]['quote'] = 'A mutated output copy.'
    assert original == before


def test_whole_section_and_duplicate_preferences_are_not_positive_requirements_for_one_move():
    original = frozen(); packet = model_packet(original)
    assert set(packet['current_brief']) == {'Writing intention','Scope and boundaries'}
    removed = packet['context_selection']['omitted_brief_fields']
    assert 'Purpose' in removed and 'Main message' in removed and 'Private coaching preferences' in removed
    assert 'Next writing action' in removed and 'An unknown later field' in removed
    assert all(field in original['current_brief'] for field in removed)
    assert 'claims actually made' in packet['review_scope']['boundary_role']
    assert 'author' in packet['review_scope']['primary_task'].lower() or 'writer_question' in packet['review_scope']['primary_task']
    assert packet['context_selection']['version'] == VERSION


def test_neighbour_contents_are_not_sent_as_current_passage_obligations():
    packet = model_packet(frozen())
    for side, ident in [('before','context'), ('after','problem')]:
        assert set(packet['outline_focus'][side]) == {'id','title','role'}
        assert packet['outline_focus'][side]['id'] == ident
        assert 'Orientation only' in packet['outline_focus'][side]['role']
    assert 'points' in packet['context_selection']['omitted_neighbour_fields']['after']
    assert packet['surrounding_draft']['after'] == '[Next idea still to write.]'


def test_no_selected_move_keeps_author_brief_including_private_preferences():
    original = frozen(); original['outline_focus'] = {'selected':None,'before':None,'after':None}
    packet = model_packet(original)
    assert packet['current_brief'] == original['current_brief']
    assert packet['outline_focus'] == original['outline_focus']
    assert packet['context_selection']['explicit_move'] is False
    assert packet['context_selection']['omitted_brief_fields'] == []


@pytest.mark.parametrize('grounding', [
    {'available':False,'coaching_records':[]},
    {'available':True,'coaching_records':[]},
])
def test_no_retrieved_records_preserve_only_guidance_fallback_as_background(grounding):
    original=frozen(); original['grounding']=grounding
    packet=model_packet(original)
    notes=packet['background_guidance']['notes']
    assert notes['Private coaching preferences']==original['current_brief']['Private coaching preferences']
    assert notes['Supervisor comments and editing consequences']==original['current_brief']['Supervisor comments and editing consequences']
    assert 'not source-checked' in packet['background_guidance']['role']
    assert 'Purpose' not in notes
    assert 'Private coaching preferences' not in packet['context_selection']['omitted_brief_fields']
    assert packet['context_selection']['curated_sources_supplied'] is False
    assert packet['grounding']==grounding


def test_selection_never_uses_prose_keywords_to_infer_coverage_or_subgoal():
    original = frozen(); original['writer_question'] = 'Only discuss the expression “a reference”.'
    original['text_to_discuss'] = 'All the later concepts appear as words here, without stated relationships.'
    packet = model_packet(original)
    assert packet['writer_question'] == original['writer_question']
    assert packet['text_to_discuss'] == original['text_to_discuss']
    assert 'coverage' not in packet and 'author_subgoal' not in packet
    assert packet['outline_focus']['selected']['id'] == 'evidence'


def test_empty_brief_and_first_or_last_move_are_valid():
    original = frozen(); original['current_brief'] = {}
    original['outline_focus']['before'] = None; original['outline_focus']['after'] = None
    packet = model_packet(original)
    assert packet['current_brief'] == {}
    assert packet['outline_focus']['before'] is packet['outline_focus']['after'] is None
    assert packet['grounding'] == original['grounding']


def test_malformed_scope_is_rejected_without_changing_saved_payload():
    with pytest.raises(ValueError):
        model_packet('not an object')
    original = frozen(); original['current_brief'] = []
    before = deepcopy(original)
    with pytest.raises(ValueError,match='brief'):
        model_packet(original)
    assert original == before


def test_edit_packet_is_a_separate_narrow_operation_and_keeps_original_private():
    from backend.coaching_context import rewrite_packet
    original=frozen();original['allow_suggestions']=True
    original['outline_focus']['selected']['writing_guide']={'write_now':['A future paragraph job.']}
    before=deepcopy(original)
    packet=rewrite_packet(original)
    assert packet['task']=='selected_passage_edit'
    assert packet['text_to_discuss']==original['text_to_discuss']
    assert packet['writer_question']==original['writer_question']
    assert packet['surrounding_draft']==original['surrounding_draft']
    assert packet['meaning_boundaries']==original['current_brief']['Scope and boundaries']
    assert 'grounding' not in packet and 'outline_focus' not in packet and 'current_brief' not in packet
    assert 'writing_guide' not in model_packet(original)['outline_focus']['selected']
    assert original==before


def test_edit_packet_requires_author_requested_selection():
    from backend.coaching_context import rewrite_packet
    original=frozen()
    with pytest.raises(ValueError):rewrite_packet(original)
    original['allow_suggestions']=True;original['submitted_scope']='whole section'
    with pytest.raises(ValueError):rewrite_packet(original)


def test_next_writing_intent_has_no_diagnostic_contract_to_fulfil():
    original=frozen();original['review_intent']='next_step'
    packet=model_packet(original)
    assert packet['review_scope']['intent']=='next_step'
    assert 'No priorities' in packet['review_scope']['intent_boundary']
