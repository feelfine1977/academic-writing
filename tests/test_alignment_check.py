from copy import deepcopy

import pytest

from backend.alignment_check import (build_check_payload, check_item_ids,
    deterministic_suggestion_flags, reconcile_check, validate_check)


def advice():
    return {'reading': 'The passage links evidence to objectives.',
            'strengths': [{'quote': 'the objective', 'explanation': 'Names the reference.'}],
            'priorities': [{'quote': '', 'kind': 'argument', 'explanation': 'Add an objective.', 'action': 'Explain the objective.'}],
            'next_question': 'Why have you not explained the objective?',
            'suggestions': [{'quote': 'Evidence can suggest a direction [].', 'replacement': 'Evidence may suggest a direction [].', 'reason': 'Keep the cautious claim.'}]}


def check(*verdicts):
    return {'decisions': [{'id': ident, 'verdict': verdict, 'reason': reason}
                         for ident, verdict, reason in verdicts]}


def codes(quote, replacement):
    return {x['code'] for x in deterministic_suggestion_flags(quote, replacement)}


def test_exact_item_coverage_required_without_new_criticism():
    proposal = advice()
    assert check_item_ids(proposal) == ['priority-0', 'suggestion-0', 'strength-0', 'next-0']
    good = check(('priority-0', 'unsupported', 'The objective is already present.'),
                 ('suggestion-0', 'supported', 'The cautious direction is retained.'),
                 ('strength-0', 'supported', 'The quoted words name the reference.'),
                 ('next-0', 'unsupported', 'The question presupposes an absent objective.'))
    assert validate_check(good, proposal) == good
    for bad in [check(('priority-0', 'supported', 'Fine.')),
                check(('priority-0', 'supported', 'Fine.'), ('priority-0', 'supported', 'Fine.')),
                check(('priority-0', 'supported', 'Fine.'), ('suggestion-2', 'supported', 'Fine.')),
                check(('priority-0', 'supported', 'Fine.'), ('suggestion-0', 'supported', 'Fine.'))]:
        with pytest.raises(ValueError):
            validate_check(bad, proposal)
    with pytest.raises(ValueError):
        validate_check({**good, 'new_advice': 'Invent another issue.'}, proposal)


def test_reconciliation_withholds_false_criticism_and_its_next_question():
    proposal = advice(); before = deepcopy(proposal)
    result, audit = reconcile_check(proposal, check(
        ('priority-0', 'unsupported', 'The objective is already stated.'),
        ('suggestion-0', 'supported', 'No content difference.'),
        ('strength-0', 'supported', 'Names the reference.'),
        ('next-0', 'unsupported', 'The objective is already stated.')))
    assert result['priorities'] == []
    assert result['suggestions'] == proposal['suggestions']
    assert 'not explained' not in result['next_question']
    assert result['reading'] == proposal['reading']
    assert audit['withheld_count'] == 2
    assert audit['original_result'] == before
    assert proposal == before


def test_unavailable_and_malformed_checks_withhold_all_actions_but_keep_audit():
    for raw, error in [(None, 'Runtime unavailable'), ({'decisions': []}, None)]:
        result, audit = reconcile_check(advice(), raw, error)
        assert result['priorities'] == result['suggestions'] == result['strengths'] == []
        assert audit['status'] == 'unavailable'
        assert audit['withheld_count'] == 4
        assert len(audit['original_result']['suggestions']) == 1
        assert audit['error']


def test_uncertain_is_not_a_vote_to_keep_an_edit():
    result, audit = reconcile_check(advice(), check(
        ('priority-0', 'supported', 'This omission is real.'),
        ('suggestion-0', 'uncertain', 'The intended modality is ambiguous.'),
        ('strength-0', 'supported', 'Names the reference.'),
        ('next-0', 'supported', 'This question addresses that omission.')))
    assert len(result['priorities']) == 1
    assert result['suggestions'] == []
    assert audit['items'][1]['verdict'] == 'uncertain'
    assert result['next_question'] == advice()['next_question']


def test_comparison_flags_catch_observed_meaning_shifts_even_if_check_says_supported():
    proposal = advice()
    proposal['suggestions'][0].update(quote='This does not establish which change will help.',
        replacement='This cannot determine which change will meet the objective without further analysis.')
    result, audit = reconcile_check(proposal, check(
        ('priority-0', 'supported', 'Applies.'), ('suggestion-0', 'supported', 'Sounds clear.'),
        ('strength-0', 'supported', 'Names the reference.'),
        ('next-0', 'supported', 'A relevant question.')))
    assert result['suggestions'] == []
    assert 'epistemic_shift' in {f['code'] for f in audit['items'][1]['comparison_flags']}
    assert 'modal_strength_change' in codes('Evidence can suggest a direction.', 'Evidence will determine the action.')
    assert 'negation_change' in codes('This is not proof.', 'This is proof.')
    assert 'epistemic_shift' in codes('This does not establish effectiveness.', 'This does not guarantee effectiveness.')


def test_citations_and_placeholders_preserved_including_empty_brackets():
    assert 'citation_change' in codes(r'The work \citep{alpha,beta} supports this [3].',
                                      r'The work \citep{alpha} supports this [3].')
    assert 'citation_change' in codes('This is supported [3].', 'This is supported [4].')
    assert 'placeholder_change' in codes('Improvement means [define this] [].', 'Improvement raises efficiency [].')
    assert 'placeholder_change' in codes('A result is needed TODO.', 'A result is available.')
    assert codes(r'The work \citep[p. 4]{alpha,beta} may explain [example] [].',
                 r'This work \citep[p. 4]{beta,alpha} may explain [example] [].') == set()


def test_alone_to_single_is_a_meaning_comparison_warning_not_a_number_rewrite():
    assert 'sufficiency_quantity_shift' in codes(
        'A score alone does not establish which change will help.',
        'A single score does not establish which change will help.')
    assert 'sufficiency_quantity_shift' not in codes(
        'A score alone does not establish which change will help.',
        'A score by itself does not establish which change will help.')
    assert 'sufficiency_quantity_shift' not in codes(
        'A single score alone does not establish which change will help.',
        'A single score by itself does not establish which change will help.')


def test_shortening_without_content_flags_is_not_certified_semantically():
    assert codes('In order to answer this question, we use the data.', 'To answer this question, we use the data.') == set()
    assert codes('This can help.', 'This can help.') == set()
    result, audit = reconcile_check({'reading': 'It works.', 'strengths': [], 'priorities': [],
                                    'suggestions': [], 'next_question': 'Write the next move.'},
                                   check(('next-0', 'supported', 'Invites continuation, not another revision.')))
    assert audit['status'] == 'checked'
    assert 'not supervisor approval' in audit['notice']
    assert result['next_question'] == 'Write the next move.'


def test_check_packet_freezes_selected_move_and_does_not_mutate_caller():
    context = {'text_to_discuss': 'A draft.', 'selected_move': {'id': 'm2'},
               'grounding': [{'id': 'g1', 'status': 'current', 'quote': 'A source.'}]}
    proposal = advice()
    packet = build_check_payload(context, proposal)
    context['selected_move']['id'] = 'm3'
    proposal['priorities'][0]['action'] = 'Changed.'
    assert packet['frozen_context']['selected_move']['id'] == 'm2'
    assert packet['items'][0]['proposal']['action'] == 'Explain the objective.'
    assert packet['items'][-1]['id'] == 'next-0'


@pytest.mark.parametrize('verdict', ['unsupported', 'uncertain'])
def test_next_question_cannot_introduce_false_defect_without_any_priorities(verdict):
    proposal = {'reading': 'The link is clear.', 'strengths': [], 'priorities': [],
                'suggestions': [], 'next_question': 'Why have you not supplied the link?'}
    before = deepcopy(proposal)
    assert check_item_ids(proposal) == ['next-0']
    result, audit = reconcile_check(proposal, check(('next-0', verdict, 'The link is already present.')))
    assert result['next_question'] == 'Continue with the next idea in your outline; keep wording that works.'
    assert audit['withheld_count'] == 1
    assert audit['original_result'] == before
    assert proposal == before


def test_unavailable_next_only_check_uses_neutral_continuation():
    proposal = {'reading': 'It works.', 'strengths': [], 'priorities': [],
                'suggestions': [], 'next_question': 'Add an unexplained new requirement.'}
    result, audit = reconcile_check(proposal, error='Timed out')
    assert result['next_question'] == 'Continue with the next idea in your outline; keep wording that works.'
    assert audit['status'] == 'unavailable'
    assert audit['items'][0]['id'] == 'next-0'
    assert not audit['items'][0]['retained']


def test_seven_items_allowed_but_next_must_be_zero():
    proposal = advice()
    proposal['priorities'] *= 2
    proposal['suggestions'] *= 2
    proposal['strengths'] *= 2
    ids = check_item_ids(proposal)
    assert len(ids) == 7
    assert validate_check(check(*[(ident, 'supported', 'Supported.') for ident in ids]), proposal)
    with pytest.raises(ValueError):
        validate_check(check(*[(ident if ident != 'next-0' else 'next-1', 'supported', 'Supported.') for ident in ids]), proposal)


def all_supported(proposal):
    return check(*[(ident, 'supported', 'Supported by the draft.') for ident in check_item_ids(proposal)])


@pytest.mark.parametrize('status', ['present', 'deferred', 'uncertain'])
def test_positive_or_future_coverage_cannot_support_missing_content_criticism(status):
    proposal = advice()
    proposal['coverage'] = [{'topic':'An objective','status':status,'quote':'the objective','reason':'The concept is accounted for.'}]
    proposal['priorities'][0]['coverage_index'] = 0
    result, audit = reconcile_check(proposal, all_supported(proposal))
    assert result['priorities'] == []
    assert audit['items'][0]['comparison_flags'][0]['code'] == 'coverage_contradiction'
    assert result['strengths'] == proposal['strengths']
    assert audit['original_result']['priorities'][0]['coverage_index'] == 0


@pytest.mark.parametrize('index', [None, -1, 1, True, '0'])
def test_missing_or_invalid_coverage_reference_is_withheld(index):
    proposal = advice()
    proposal['coverage'] = [{'topic':'A connection','status':'needs_work_now','quote':'','reason':'The relation is missing.'}]
    if index is not None:
        proposal['priorities'][0]['coverage_index'] = index
    result, audit = reconcile_check(proposal, all_supported(proposal))
    assert result['priorities'] == []
    assert audit['items'][0]['comparison_flags'][0]['code'] == 'coverage_reference'


def test_needed_coverage_and_supported_check_can_retain_one_current_action():
    proposal = advice()
    proposal['coverage'] = [{'topic':'A connection','status':'needs_work_now','quote':'','reason':'The current relation is missing.'}]
    proposal['priorities'][0]['coverage_index'] = 0
    result, audit = reconcile_check(proposal, all_supported(proposal))
    assert result['priorities'] == proposal['priorities']
    assert audit['withheld_count'] == 0
    packet = build_check_payload({'text_to_discuss':'A draft.'}, proposal)
    proposal['coverage'][0]['status'] = 'present'
    assert packet['proposed_coverage'][0]['status'] == 'needs_work_now'


@pytest.mark.parametrize('verdict', ['unsupported', 'uncertain'])
def test_false_praise_is_not_retained_as_a_positive_judgement(verdict):
    proposal = {'reading':'Two ideas are mentioned.', 'coverage':[], 'priorities':[], 'suggestions':[],
                'strengths':[{'quote':'Ideas. Findings.', 'explanation':'Clearly explains how the findings answer the question.'}],
                'next_question':'Continue to the next idea.'}
    result, audit = reconcile_check(proposal, check(
        ('strength-0', verdict, 'The words merely juxtapose the concepts; no relation is stated.'),
        ('next-0', 'supported', 'The author can continue.')))
    assert result['strengths'] == []
    assert audit['original_result']['strengths'] == proposal['strengths']
    assert audit['withheld_count'] == 1


@pytest.mark.parametrize('action', ['Rewrite to: Evidence determines the action.',
                                    'Replace this with: Evidence determines the action.',
                                    "Insert: 'However, all findings determine the intervention.'",
                                    'Add the sentence: “This proves the outcome.”',
                                    'Replace "can suggest" with "will determine".'])
def test_replacement_cannot_hide_in_an_action_when_not_requested(action):
    proposal = advice()
    proposal['priorities'][0]['action'] = action
    result, audit = reconcile_check(proposal, all_supported(proposal), context={'allow_suggestions':False})
    assert result['priorities'] == []
    assert audit['items'][0]['comparison_flags'][0]['code'] == 'hidden_replacement'
    # Compatibility: only a supplied frozen context activates this guard.
    without_context, _ = reconcile_check(proposal, all_supported(proposal))
    assert without_context['priorities'] == proposal['priorities']


def test_action_can_ask_author_to_revise_without_giving_replacement_text():
    proposal = advice()
    proposal['priorities'][0]['action'] = 'Replace vague references with the names of the actors you mean.'
    result, audit = reconcile_check(proposal, all_supported(proposal), context={'allow_suggestions':False})
    assert result['priorities'] == proposal['priorities']
    assert audit['withheld_count'] == 0
    proposal['priorities'][0]['action']='Insert a brief explanation of the relationship you mean.'
    result,audit=reconcile_check(proposal,all_supported(proposal),context={'allow_suggestions':False})
    assert result['priorities']==proposal['priorities']
    assert audit['withheld_count']==0


@pytest.mark.parametrize('use_second_reading',[False,True])
def test_unrequested_replacement_in_explanation_is_withheld_in_both_paths(use_second_reading):
    from backend.alignment_check import reconcile_without_check
    proposal=advice()
    proposal['priorities'][0]['explanation']=(
        "The reader needs a link. Add: 'By establishing the research question, we can identify which observations are relevant to answering it.'")
    context={'allow_suggestions':False,'writer_question':'Help me connect these ideas; do not rewrite my text.'}
    if use_second_reading:
        result,audit=reconcile_check(proposal,all_supported(proposal),context=context)
    else:
        result,audit=reconcile_without_check(proposal,context)
    assert result['priorities']==[]
    assert 'hidden_replacement' in {flag['code'] for flag in audit['items'][0]['comparison_flags']}
    assert audit['original_result']['priorities']==proposal['priorities']
    # An instruction to write a missing explanation still leaves authorship to
    # the writer and is not the same thing as supplying a replacement sentence.
    proposal['priorities'][0]['explanation']='Add context about the relationship you intend to explain.'
    result,audit=reconcile_without_check(proposal,context)
    assert result['priorities']==proposal['priorities']
    assert audit['withheld_count']==0


def test_unknown_verdict_does_not_become_successful_check_or_positive_feedback():
    proposal = advice()
    invalid = all_supported(proposal)
    invalid['decisions'][0]['verdict'] = 'probably fine'
    result, audit = reconcile_check(proposal, invalid)
    assert audit['status'] == 'unavailable'
    assert result['strengths'] == result['priorities'] == result['suggestions'] == []
    assert audit['original_result'] == proposal


def test_single_reading_is_not_labelled_checked_and_preserves_raw_judgement():
    from backend.alignment_check import reconcile_without_check
    proposal=advice();before=deepcopy(proposal)
    result,audit=reconcile_without_check(proposal,{'allow_suggestions':False})
    assert result==proposal and proposal==before
    assert audit['status']=='not_requested' and audit['provisional']
    assert audit['check_result'] is None
    assert 'No second reading was requested or performed' in audit['notice']
    assert all(item['verdict']=='not_checked' for item in audit['items'])
    result['strengths'][0]['explanation']='A changed output copy.'
    assert audit['original_result']==before and proposal==before


def test_single_reading_still_applies_coverage_and_hidden_rewrite_guards():
    from backend.alignment_check import reconcile_without_check
    proposal=advice()
    proposal['coverage']=[{'topic':'The link','status':'present','quote':'the objective','reason':'It is already connected.'}]
    proposal['priorities'][0].update(coverage_index=0,action="Insert: 'The objective guarantees the action.'")
    result,audit=reconcile_without_check(proposal,{'allow_suggestions':False})
    assert result['priorities']==[]
    assert result['strengths']==proposal['strengths']  # provisional, not independently endorsed
    assert {flag['code'] for flag in audit['items'][0]['comparison_flags']}=={'coverage_contradiction','hidden_replacement'}
    assert result['next_question']=='Continue with the next idea in your outline; keep wording that works.'
    assert audit['status']=='not_requested' and audit['original_result']==proposal


def test_single_reading_edit_flags_remain_conservative_without_semantic_check():
    from backend.alignment_check import reconcile_without_check
    proposal=advice()
    proposal['suggestions'][0].update(quote='A score alone can guide the next question [].',
                                      replacement='A single score will guide the intervention.')
    result,audit=reconcile_without_check(proposal,{'allow_suggestions':True})
    assert result['suggestions']==[]
    codes={flag['code'] for flag in audit['items'][1]['comparison_flags']}
    assert {'sufficiency_quantity_shift','modal_strength_change','placeholder_change'}<=codes
    assert audit['check_result'] is None and audit['status']=='not_requested'


def test_literal_edit_guards_cover_modal_removal_data_and_technical_abbreviations():
    assert 'weak_modal_removed' in codes('The logs can suggest a direction.', 'The logs suggest a direction.')
    assert 'weak_modal_removed' not in codes('The logs can suggest a direction.', 'The logs may suggest a direction.')
    assert 'epistemic_predicate_change' in codes('The results do not establish effectiveness.', 'The results do not determine effectiveness.')
    assert 'number_change' in codes('We observed 12 cases.', 'We observed 21 cases.')
    assert 'number_change' not in codes('We observed 12 cases [2].', 'There were 12 observed cases [2].')
    assert 'abbreviation_change' in codes('The P2P trace indicates delay.', 'The trace indicates delay.')
    assert not codes('The P2P trace can indicate delay [2].', 'Delay can appear in the P2P trace [2].')


def test_diagnostic_contract_requires_anchored_counterevidence():
    from backend.alignment_check import reconcile_without_check
    proposal=advice();proposal['suggestions']=[]
    context={'text_to_discuss':'Evidence is interpreted relative to the objective.',
             'review_scope':{'diagnosis_contract':1},'allow_suggestions':False}
    result,audit=reconcile_without_check(proposal,context)
    assert not result['priorities']
    assert audit['items'][0]['comparison_flags'][0]['code']=='missing_counterevidence'
    proposal['priorities'][0]['evidence']={'already_present_quote':'A fabricated quote.', 'why_still_needed':'It fails.'}
    result,audit=reconcile_without_check(proposal,context)
    assert not result['priorities']
    assert audit['items'][0]['comparison_flags'][0]['code']=='unanchored_counterevidence'


def test_repair_constraints_are_external_exact_spans_and_rechecked():
    from backend.alignment_check import edit_repair_constraints,repaired_edit_flags
    text=r'P2P evidence can suggest a direction, but alone does not establish a benefit \cite{sample}.'
    rejected='Evidence suggests a direction but cannot determine a benefit.'
    constraints=edit_repair_constraints(text,rejected)
    assert {'P2P','can','alone','does not establish',r'\cite{sample}'}-set(constraints['original_spans_to_keep'])=={'alone'}
    # “alone” was omitted, rather than replaced with “single”; this particular
    # guard does not claim to detect that omission. Exact modals/citations do fire.
    assert repaired_edit_flags(text,text,constraints)==[]
    changed=text.replace('can','may')
    assert 'repair_contract_not_restored' in {f['code'] for f in repaired_edit_flags(text,changed,constraints)}
    assert edit_repair_constraints('To answer this, we use records.','We use records to answer this.') is None
