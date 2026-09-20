"""Select model context without changing the saved author/review snapshot.

This is a structural scope filter, not an interpretation of the prose. It does
not use keywords to decide whether the author has covered an idea. Source
records and the submitted writing remain exact copies for later comparison.
"""
from copy import deepcopy

VERSION = 'coaching-context-2'

# These two fields may help orient a selected-move reading without importing
# the whole section's positive requirements. A boundary forbids a claim only
# when the draft actually makes it; it does not require repeating the caveat.
_MOVE_BRIEF_FIELDS = ('Writing intention', 'Scope and boundaries')


def model_packet(frozen_payload):
    """Return an isolated, bounded-context view of a frozen section payload.

    The caller must retain ``frozen_payload`` as the private full snapshot and
    use this returned packet for both the first reading and its advice check.
    Hash/version this packet alongside the original snapshot for reproducibility.
    No field is semantically rewritten or truncated here.
    """
    if not isinstance(frozen_payload, dict):
        raise ValueError('A section coaching packet must be an object.')
    packet = deepcopy(frozen_payload)
    focus = packet.get('outline_focus')
    selected = focus.get('selected') if isinstance(focus, dict) else None
    explicit = isinstance(selected, dict) and bool(selected.get('id'))
    grounding = packet.get('grounding', {})
    has_sources = bool(isinstance(grounding, dict) and grounding.get('available') and
                       (grounding.get('coaching_records') or grounding.get('requirements')))
    omitted = []
    background = []
    neighbour_fields = {}
    if explicit:
        # App-side writing aids are not additional grading criteria. Keep them
        # available in the original snapshot without feeding a duplicate rubric.
        selected.pop('writing_guide', None)
        brief = packet.get('current_brief', {})
        if not isinstance(brief, dict):
            raise ValueError('The saved section brief must be an object.')
        omitted = [field for field in brief if field not in _MOVE_BRIEF_FIELDS]
        packet['current_brief'] = {field: brief[field] for field in _MOVE_BRIEF_FIELDS if field in brief}
        if not has_sources:
            # Without retrieved sources these notes may be the only private
            # coaching guidance. Preserve them as background, not a rubric.
            background = [field for field in ('Private coaching preferences', 'Supervisor comments and editing consequences')
                          if brief.get(field)]
            if background:
                packet['background_guidance'] = {
                    'role': 'Fallback private guidance, not source-checked supervisor excerpts or additional requirements for this passage. Apply only when relevant to the author question.',
                    'notes': {field: brief[field] for field in background},
                }
                omitted = [field for field in omitted if field not in background]
        for side in ('before', 'after'):
            neighbour = focus.get(side)
            if neighbour is None:
                continue
            if not isinstance(neighbour, dict):
                raise ValueError('An outline neighbour must be an object or null.')
            neighbour_fields[side] = [field for field in neighbour if field not in ('id', 'title')]
            focus[side] = {field: neighbour[field] for field in ('id', 'title') if field in neighbour}
            focus[side]['role'] = 'Orientation only; not required content in this submitted passage.'
        focus['notice'] = ('The selected move provides orientation. The author’s question and actual submitted text define this reading. '
                           'Do not require every point in the selected move at once; neighbours show position only.')
    packet['review_scope'] = {
        'primary_task': 'Answer writer_question about text_to_discuss. Identify an actual defect before requesting a revision.',
        'move_role': ('An explicitly selected move identifies where the author is working, not a compulsory checklist for this passage.'
                      if explicit else 'No single move is selected. Follow the submitted scope and author question.'),
        'boundary_role': 'Apply a scope boundary only to claims actually made. Absence of a later idea or caveat is not itself a false claim.',
        'source_role': 'The unchanged grounding records are conditional teaching guidance. Preserve their scope, permissions and exceptions.',
        'next_step_role': 'A later writing action can be an invitation to continue, never evidence that the current passage is defective.',
    }
    intent = packet.get('review_intent', 'discussion')
    packet['review_scope']['intent'] = intent
    packet['review_scope']['diagnosis_contract'] = 1
    packet['review_scope']['intent_boundary'] = (
        'Give one next writing action, not a diagnosis of this passage. No priorities or replacement wording.'
        if intent == 'next_step' else
        'Check only the connection named in the author question. Later outline coverage is outside this check.'
        if intent == 'connection' else
        'Answer the author question first. A broader review was not automatically requested.')
    packet['context_selection'] = {
        'version': VERSION,
        'explicit_move': explicit,
        'curated_sources_supplied': has_sources,
        'omitted_brief_fields': omitted,
        'background_brief_fields': background,
        'omitted_neighbour_fields': neighbour_fields,
        'notice': ('Broad section requirements were omitted from this selected-move model view. '
                   + ('Retrieved records replace duplicate private guidance. ' if has_sources else 'Private coaching notes are retained as fallback background when available. ')
                   + 'The original saved context is retained separately; the submitted writing and retrieved source records are unchanged.'
                   if explicit else 'The section brief is unchanged because no single outline move was selected.'),
    }
    return packet


def rewrite_packet(frozen_payload):
    """A separate edit contract; broad teaching material is not an edit rubric.

    Keep the exact selection, nearby prose, boundaries and current author request.
    The original RAG packet remains in the private review record. No model is
    asked to paraphrase source records or infer a new outline for a surface edit.
    """
    packet = model_packet(frozen_payload)
    if not packet.get('allow_suggestions') or packet.get('submitted_scope') != 'selected passage':
        raise ValueError('A scoped edit requires an explicitly requested selected passage.')
    return {
        'task': 'selected_passage_edit',
        'writer_question': packet['writer_question'],
        'text_to_discuss': packet['text_to_discuss'],
        'surrounding_draft': deepcopy(packet.get('surrounding_draft', {})),
        'stage': packet.get('stage', 'rewrite'),
        'meaning_boundaries': packet.get('current_brief', {}).get('Scope and boundaries', ''),
        'writing_intention': packet.get('current_brief', {}).get('Writing intention', ''),
        'allow_demonstration': packet.get('allow_demonstration', False),
        'source_conflicts': deepcopy(packet.get('grounding', {}).get('conflicts', [])),
        'context_selection': {
            'version': VERSION, 'operation': 'selected_passage_edit',
            'notice': 'Only the selected text, nearby prose, author request and meaning boundaries are used for this wording edit. The complete review context is retained separately.'
        },
    }
