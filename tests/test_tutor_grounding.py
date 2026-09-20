"""Generic, isolated contracts for private local guidance retrieval.

These tests establish provenance, scope and bounds, not academic judgement.
"""
import json
from pathlib import Path

import pytest

from backend import tutor_grounding as grounding


TRANSCRIPT = (
    'P0001 Tutor: Establish the concepts before contrasting them.\n'
    'P0002 Tutor: Either opening order can work if the connections are clear.\n'
    'P0003 Tutor: Preserve uncertainty when revising a claim.\n'
    'P0004 Tutor: The problem statement can replace the separate question.\n'
)


def requirement(ident='concepts', *, quote='Establish the concepts before contrasting them.',
                paragraphs=None, stage=None, scope=None, **extra):
    return {
        'id': ident, 'instruction': quote, 'kind': 'teaching_guidance',
        'strength': 'explicit', 'status': 'active',
        'stage': stage or ['connect', 'rewrite'],
        'scope': scope or {'section_id': 'section-alpha', 'moves': []},
        'evidence': [{'source_id': 'meeting', 'quote': quote,
                      'paragraphs': ['P0001'] if paragraphs is None else paragraphs}],
        **extra,
    }


def install(root, rows, *, transcript=TRANSCRIPT, source=None):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'Sources').mkdir(exist_ok=True)
    (root / 'Sources' / 'meeting.txt').write_text(transcript, encoding='utf-8')
    index = {
        'schema_version': 1,
        'source_documents': [source or {
            'id': 'meeting', 'path': 'Sources/meeting.txt',
            'title': 'A private teaching discussion', 'date': '2026-09-18',
            'sha256': grounding.digest(transcript),
        }],
        'requirements': rows,
    }
    (root / 'Tutor knowledge.md').write_text(
        '# Local guidance\n\n```json\n' + json.dumps(index) + '\n```\n', encoding='utf-8')
    return index


def retrieved(root, **kwargs):
    return grounding.retrieve(root, 'section-alpha', 'Introduction', 'connect', **kwargs)


def ids(result):
    return [r['id'] for r in result['requirements']]


def test_absent_knowledge_has_honest_generic_fallback(tmp_path):
    result = retrieved(tmp_path)
    assert result['available'] is False
    assert result['requirements'] == []
    assert result['general_bases']
    assert any('general writing guidance' in note for note in result['notices'])
    assert not (tmp_path / 'Tutor knowledge.md').exists()


def test_scope_stage_move_and_neighbours_are_distinct(tmp_path):
    rows = [
        requirement('current', scope={'section_id': 'section-alpha', 'moves': ['context']}),
        requirement('later', scope={'section_id': 'section-alpha', 'moves': ['problem']}),
        requirement('other-section', scope={'section_id': 'section-beta', 'moves': []}),
        requirement('polish-only', stage=['polish']),
    ]
    install(tmp_path, rows)
    assert ids(retrieved(tmp_path, move_id='context')) == ['current']
    assert ids(retrieved(tmp_path)) == []  # no selected move must not imply every move
    steps = [{'id': 'context', 'title': 'Context', 'purpose': 'Introduce the topic'},
             {'id': 'problem', 'title': 'Problem', 'purpose': 'Explain the difficulty'},
             {'id': 'response', 'title': 'Response', 'purpose': 'Describe the approach'}]
    orientation = grounding.move_context(steps, 'problem')
    assert orientation['selected']['id'] == 'problem'
    assert orientation['before']['id'] == 'context'
    assert orientation['after']['id'] == 'response'
    assert 'orientation only' in orientation['notice']
    with pytest.raises(ValueError, match='selected outline idea changed'):
        grounding.move_context(steps, 'removed')


def test_explicit_section_identity_cannot_match_title_substring(tmp_path):
    install(tmp_path, [requirement('unrelated', scope={'section_id': 'intro', 'moves': []})])
    assert ids(retrieved(tmp_path)) == []


@pytest.mark.parametrize('change', ['hash', 'quote', 'locator'])
def test_changed_or_misattributed_source_is_excluded(tmp_path, change):
    row = requirement()
    if change == 'quote':
        row['evidence'][0]['quote'] = 'An invented instruction absent from the record.'
    if change == 'locator':
        row['evidence'][0]['paragraphs'] = ['P0003']
    install(tmp_path, [row])
    if change == 'hash':
        with (tmp_path / 'Sources' / 'meeting.txt').open('a', encoding='utf-8') as stream:
            stream.write('P0005 Later addition.\n')
    result = retrieved(tmp_path)
    assert result['requirements'] == []
    assert any('excluded' in note.lower() for note in result['notices'])
    reason = {'hash': 'source changed', 'quote': 'not found', 'locator': 'numbered locator'}[change]
    assert any(reason in note.lower() for note in result['notices'])


def test_matching_quote_with_whitespace_variation_keeps_locator_provenance(tmp_path):
    install(tmp_path, [requirement(quote='Establish  the concepts\nbefore contrasting them.')])
    result = retrieved(tmp_path,query='concepts')
    assert ids(result) == ['concepts']
    evidence = result['requirements'][0]['evidence'][0]
    assert evidence['locator'] == 'P0001'
    assert evidence['hash'] == grounding.digest(TRANSCRIPT)
    assert evidence['source_id'] == 'meeting'
    assert 'not supervisor approval' in result['notice']


def test_superseded_record_stays_auditable_but_is_not_required(tmp_path):
    rows = [
        requirement('old-order'),
        requirement('new-order', quote='Either opening order can work if the connections are clear.',
                    paragraphs=['P0002'], supersedes=['old-order']),
        requirement('historical-note', status='historical'),
    ]
    install(tmp_path, rows)
    result = retrieved(tmp_path,query='clear connections')
    assert ids(result) == ['new-order']
    assert result['excluded_historical'] == ['historical-note', 'old-order']


def test_equal_current_conflicts_are_withheld_without_choosing_a_winner(tmp_path):
    install(tmp_path, [requirement('first', conflicts_with=['second']),
                       requirement('second'), requirement('independent')])
    result = retrieved(tmp_path,query='concepts')
    assert ids(result) == ['independent']
    assert result['conflicts'] == [['first', 'second']]
    assert any('Conflicting current guidance was excluded' in note for note in result['notices'])


def test_retrieval_caps_records_and_preserves_whole_quoted_records(tmp_path):
    records = [requirement(f'item-{i}') for i in range(9)]
    records[-1]['instruction'] = 'Preserve modality and uncertainty, especially a tentative claim.'
    install(tmp_path, records)
    result = retrieved(tmp_path, query='concepts modality uncertainty tentative', max_records=3)
    assert len(result['requirements']) == 3
    assert ids(result)[0] == 'item-8'
    assert all(r['evidence'][0]['quote'] == records[0]['evidence'][0]['quote']
               for r in result['requirements'])
    # Large records may be left out, but a quotation must not be silently truncated.
    quote = 'P' * 2000
    source = 'P0001 ' + quote + '\n'
    big = [requirement(f'large-{i}', quote=quote, instruction='I' * 1700) for i in range(8)]
    install(tmp_path, big, transcript=source)
    large_result = retrieved(tmp_path, query='I'*1700, max_records=8)
    assert 0 < len(large_result['requirements']) < 8
    assert all(r['evidence'][0]['quote'] == quote for r in large_result['requirements'])
    assert sum(len(json.dumps(r, ensure_ascii=False)) for r in large_result['requirements']) <= 8500


@pytest.mark.parametrize('path', ['../secret.txt', '/tmp/secret.txt', 'Sources/model.py'])
def test_arbitrary_source_paths_are_never_opened(tmp_path, path):
    source = {'id': 'meeting', 'path': path, 'title': 'Invalid path'}
    install(tmp_path, [requirement()], source=source)
    result = retrieved(tmp_path)
    assert result['available'] is False
    assert result['requirements'] == []
    assert any('guidance' in n.lower() or 'source' in n.lower() for n in result['notices'])


def test_symlink_source_and_symlink_index_are_rejected(tmp_path):
    root = tmp_path / 'paper'
    install(root, [requirement()])
    outside = tmp_path / 'outside.txt'
    outside.write_text(TRANSCRIPT, encoding='utf-8')
    source = root / 'Sources' / 'meeting.txt'
    source.unlink()
    source.symlink_to(outside)
    assert retrieved(root)['available'] is False
    source.unlink()
    source.write_text(TRANSCRIPT, encoding='utf-8')
    index = root / 'Tutor knowledge.md'
    outside_index = tmp_path / 'outside.md'
    outside_index.write_text(index.read_text(encoding='utf-8'), encoding='utf-8')
    index.unlink()
    index.symlink_to(outside_index)
    assert retrieved(root)['available'] is False


def test_source_change_invalidates_fingerprint_and_requires_reindex(tmp_path):
    index = install(tmp_path, [requirement()])
    before = retrieved(tmp_path)
    changed = TRANSCRIPT + 'P0005 Preserve a useful earlier sentence.\n'
    (tmp_path / 'Sources' / 'meeting.txt').write_text(changed, encoding='utf-8')
    after = retrieved(tmp_path)
    assert after['fingerprint'] != before['fingerprint']
    assert after['requirements'] == []
    index['source_documents'][0]['sha256'] = grounding.digest(changed)
    (tmp_path / 'Tutor knowledge.md').write_text(json.dumps(index), encoding='utf-8')
    reindexed = retrieved(tmp_path,query='concepts')
    assert ids(reindexed) == ['concepts']
    assert reindexed['fingerprint'] != after['fingerprint']


def test_bad_index_does_not_claim_supervisor_alignment(tmp_path):
    (tmp_path / 'Tutor knowledge.md').write_text('{ broken json', encoding='utf-8')
    result = retrieved(tmp_path)
    assert result['available'] is False
    assert result['requirements'] == []
    assert any('cannot claim to follow these records' in note for note in result['notices'])


def test_zero_relevance_records_do_not_fill_retrieval_quota(tmp_path):
    rows=[requirement('unrelated'), requirement('relevant',
          quote='Preserve uncertainty when revising a claim.',paragraphs=['P0003'])]
    install(tmp_path,rows)
    result=retrieved(tmp_path,query='uncertainty claim',max_records=5)
    assert ids(result)==['relevant']
    assert result['eligible_count']==2 and result['retrieved_count']==1
    no_match=retrieved(tmp_path,query='punctuation semicolons')
    assert no_match['requirements']==[]
    assert 'No supervisor excerpt was supplied' in no_match['notice']
    assert 'Source quotations were matched' not in no_match['notice']


def test_empty_query_only_uses_explicit_defaults_or_exact_move(tmp_path):
    install(tmp_path,[requirement('not-a-default'),
                      requirement('explicit-default',default_for_stage=True),
                      requirement('truthy-string-is-not-default',default_for_stage='yes'),
                      requirement('selected-move',scope={'section_id':'section-alpha','moves':['m1']})])
    assert ids(retrieved(tmp_path))==['explicit-default']
    assert ids(retrieved(tmp_path,move_id='m1'))==['selected-move','explicit-default']
    assert ids(retrieved(tmp_path,query='irrelevantword'))==[]


def test_legacy_bridge_becomes_model_move_connection_without_overriding_new_field():
    steps=[{'id':'first','title':'First','bridge':'What follows from the observation?'},
           {'id':'second','title':'Second','bridge':'Old bridge.','bridge_question':'Current bridge.'}]
    context=grounding.move_context(steps,'first')
    assert context['selected']['bridge_question']=='What follows from the observation?'
    assert context['after']['bridge_question']=='Current bridge.'
    assert 'bridge_question' not in steps[0]  # original portable card stays unchanged


@pytest.mark.parametrize('value', ['Already supplied.', None, [3], ['x'*1001], ['x']*21])
def test_malformed_exception_list_excludes_record_with_visible_notice(tmp_path,value):
    install(tmp_path,[requirement(not_applicable_when=value)])
    original=(tmp_path/'Tutor knowledge.md').read_bytes()
    result=retrieved(tmp_path,query='concepts')
    assert result['available'] is True  # the file loaded, but its record is unusable
    assert result['requirements']==[]
    assert any('not_applicable_when' in notice and 'excluded' in notice for notice in result['notices'])
    assert 'No supervisor excerpt was supplied' in result['notice']
    assert (tmp_path/'Tutor knowledge.md').read_bytes()==original


@pytest.mark.parametrize('value', [{'example':'Not a text field.'}, ['A sentence.'], None, 'x'*2401])
def test_malformed_example_does_not_become_prompt_content_or_hide_other_guidance(tmp_path,value):
    install(tmp_path,[requirement('invalid-example',positive_example=value),
                      requirement('valid-example',positive_example='Introduce the two ideas, then state their relationship.',
                                  not_applicable_when=['The relationship is already expressed.'])])
    result=retrieved(tmp_path,query='concepts')
    assert ids(result)==['valid-example']
    assert result['requirements'][0]['not_applicable_when']==['The relationship is already expressed.']
    assert result['requirements'][0]['positive_example']=='Introduce the two ideas, then state their relationship.'
    assert any('invalid-example' in notice and 'positive_example' in notice and 'excluded' in notice
               for notice in result['notices'])
