import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.section_writing import SectionWriting, parse_steps, validate_advice, supervisor_instruction, rewrite_advice
from backend.storage import Store
from backend.workspace import Workspace, Conflict, sha
from backend.workspace_latex import latex_preview


@pytest.fixture
def desk(tmp_path):
    vault=tmp_path/'Vault';(vault/'.obsidian').mkdir(parents=True)
    lab=SimpleNamespace(vault=vault,store=Store(tmp_path/'data'),tasks={},semaphore=asyncio.Semaphore(1))
    lab.workspace=Workspace(lab);lab.workspace.configure(str(vault))
    plan=lab.workspace.create('Our paper','## Section: Introduction\n### Argument: First\n### Manuscript prose\nEarlier child text.\n## Section: Method\n### Argument: Method argument\n### Manuscript prose\nMethod text.')
    section=next(n for n in plan['nodes'] if n['type']=='section')
    section=lab.workspace.card(plan['id'],section['id'])
    lab.store.set_setting('profile',{'provider':'ollama','model':'test-model','local_confirmed':True})
    return SectionWriting(lab),plan['id'],section['id']


def save(app,pid,sid,fields):
    note=app.section(pid,sid)
    return app.ws.save(pid,sid,note['hash'],fields)


def test_whole_section_export_owns_children_without_deleting_them(desk):
    app,pid,sid=desk
    text='This is my connected introduction.'
    note=save(app,pid,sid,{'Manuscript prose':text,'Section manuscript source':'section','Completed prose hash':sha(text),
                         'Writing scaffold':'Private scaffolding.','Writing outline':'Private planned ideas.'})
    result=latex_preview(app.ws,pid,{'section_ids':[sid]})
    assert [n['id'] for n in result['included']]==[sid]
    assert '\\section{Introduction}' in result['tex']
    assert text in result['tex'] and 'Earlier child' not in result['tex'] and 'Private' not in result['tex']
    assert text in app.ws.export(pid) and 'Earlier child' not in app.ws.export(pid)
    child=next(n for n in app.ws.get(pid)['nodes'] if n['type']=='argument')
    assert child['fields']['Manuscript prose']=='Earlier child text.'
    # Selecting the old argument cannot bypass its section's declared authority.
    child_selection=latex_preview(app.ws,pid,{'card_ids':[child['id']]})
    assert child_selection['included'][0]['id']==sid
    assert any('authoritative whole-section draft' in warning for warning in child_selection['warnings'])
    save(app,pid,sid,{'Manuscript prose':'A revised introduction.'})
    revised=latex_preview(app.ws,pid,{'section_ids':[sid]})
    assert not revised['included'] and revised['skipped'][0]['reason']=='not_approved'
    assert 'Earlier child' not in revised['tex']
    # Markdown is the existing working-manuscript export, so it includes saved
    # drafts. The separate approved LaTeX export above must not include them.
    assert 'A revised introduction.' in app.ws.export(pid)
    assert 'Private scaffolding' not in app.ws.export(pid)
    save(app,pid,sid,{'Section manuscript source':'arguments'})
    assert 'Earlier child text.' in app.ws.export(pid)


def test_empty_authoritative_section_never_falls_back_to_child(desk):
    app,pid,sid=desk;save(app,pid,sid,{'Section manuscript source':'section'})
    result=latex_preview(app.ws,pid,{'section_ids':[sid]})
    assert result['included']==[] and result['skipped'][0]['reason']=='empty'
    assert 'Earlier child' not in app.ws.export(pid)


def test_unknown_manuscript_source_edited_in_obsidian_does_not_silently_export_children(desk):
    app,pid,sid=desk;note=save(app,pid,sid,{'Section manuscript source':'section'})
    path=Path(note['path']);path.write_text(path.read_text().replace('## Section manuscript source\n\nsection','## Section manuscript source\n\nwhole'))
    with pytest.raises(ValueError,match='manuscript source'):app.ws.export(pid)
    with pytest.raises(ValueError,match='manuscript source'):latex_preview(app.ws,pid,{'section_ids':[sid]})


def test_section_fields_validation_and_plan_roundtrip(desk):
    app,pid,sid=desk
    moves=[{'id':'context','title':'Process mining evidence','points':['What can an event log show?'],'bridge':'Why does that evidence need interpretation?'}]
    note=save(app,pid,sid,{'Section writing plan':'```json\n'+json.dumps({'steps':moves})+'\n```',
                         'Section writing stage':'connect','Outline provenance':'Meeting 21: recorded guidance.'})
    value=app.writing(pid,sid)
    assert value['steps']==moves and value['section']['hash']==note['hash']
    assert value['tutor_profiles'][0]['id']=='narrative'
    with pytest.raises(ValueError):save(app,pid,sid,{'Section manuscript source':'guess'})
    with pytest.raises(ValueError):save(app,pid,sid,{'Section writing stage':'grade'})
    with pytest.raises(ValueError):parse_steps(json.dumps([moves[0],moves[0]]))
    before=app.section(pid,sid)
    with pytest.raises(ValueError):save(app,pid,sid,{'Section writing plan':'```json\n{broken\n```'})
    assert app.section(pid,sid)['hash']==before['hash']
    with pytest.raises(ValueError):save(app,pid,sid,{'Writing scaffold':'Planning\n## Manuscript prose\nInjected'})


ADVICE={'reading':'Your paragraph introduces the role of evidence.',
        'strengths':[{'quote':'My own introduction.','explanation':'The reader can identify your topic.'}],
        'priorities':[{'quote':'','kind':'meaning_question','explanation':'The next connection remains open.','action':'Explain why the reader needs this distinction.',
                       'evidence':{'already_present_quote':'','why_still_needed':'The submitted words do not identify the connection requested in this fixture.'}}],
        'next_question':'What does this evidence allow the reader to understand next?','suggestions':[]}


def supported_check(payload):
    return {'decisions':[{'id':item['id'],'verdict':'supported','reason':'Supported by this frozen draft and scope.'}
                         for item in payload['items']]}


def edit_response(replacement, explanation='A small optional shortening.'):
    return {'decision':'edit','replacement':replacement,'explanation':explanation,'clarification':''}


def test_review_snapshot_remains_available_while_writer_changes_draft(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;note=save(app,pid,sid,{'Manuscript prose':'My own introduction.','Section manuscript source':'section'})
        started=asyncio.Event();release=asyncio.Event();seen={}
        async def generate(profile,payload,mode,model):
            if mode=='section_alignment_check':return supported_check(payload),{'model':'test-checker'}
            seen.update(payload);assert mode=='section_supervisor';started.set();await release.wait()
            return ADVICE,{'model':'test-model'}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{'base_hash':note['hash'],'text':'My own introduction.','question':'How can I connect these ideas?'})
        await started.wait()
        save(app,pid,sid,{'Manuscript prose':'My revised introduction while waiting.','Writing outline':'My changed section plan.'})
        plan=app.ws.get(pid)
        app.ws.save(pid,pid,plan['hash'],{'Agreed plan and open questions':'A new outline decision while the tutor reads.'})
        release.set();await asyncio.gather(*list(app.lab.tasks.values()))
        result=app.review_status(pid,sid,job['id'])
        assert result['status']=='complete' and result['text']=='My own introduction.'
        assert result['result']==ADVICE and seen['text_to_discuss']=='My own introduction.'
        assert seen['current_brief']['Writing outline']=='' and result['outline_hash']!=app.ws.get(pid)['hash']
        assert app.section(pid,sid)['fields']['Manuscript prose']=='My revised introduction while waiting.'
        assert app.section(pid,sid)['writing_status']=='draft'
        assert len(list((app.root(pid)/'Reviews').glob('*.md')))==2
        # A second computer can read the immutable vault feedback without SQLite.
        app.store=Store(app.store.directory.parent/'other-data')
        assert app.review_status(pid,sid,job['id'])['status']=='complete'
        # An interrupted request restored on that computer must not mask the
        # completed feedback later delivered by Obsidian Sync, even with clock skew.
        app.store.set_setting('section_review:'+job['id'],{**result,'status':'interrupted','result':None,'finished':'2099-01-01'})
        assert app.review_status(pid,sid,job['id'])['status']=='complete'
    asyncio.run(run())


def test_stale_or_unsaved_review_is_rejected(desk):
    async def run():
        app,pid,sid=desk;note=save(app,pid,sid,{'Manuscript prose':'My own introduction.'})
        with pytest.raises(Conflict):await app.review(pid,sid,{'base_hash':note['hash'],'text':'Unsaved text.','question':'Read it.'})
        with pytest.raises(Conflict):await app.review(pid,sid,{'base_hash':'old','text':'My own introduction.','question':'Read it.'})
        assert not app.lab.tasks
    asyncio.run(run())


def test_long_section_requires_explicit_selection_and_preserves_full_snapshot(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;draft='Earlier discussion. '*1300+'My own introduction.'
        note=save(app,pid,sid,{'Manuscript prose':draft})
        body={'base_hash':note['hash'],'text':draft,'question':'Help me connect the ideas.'}
        with pytest.raises(ValueError,match='select a passage'):await app.review(pid,sid,body)
        seen={}
        async def generate(profile,payload,mode,model):
            if mode=='section_alignment_check':return supported_check(payload),{}
            assert mode=='section_supervisor';seen.update(payload);return ADVICE,{}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{**body,'selected_text':'My own introduction.'})
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert job['text']==draft and job['scope']=='selected passage'
        assert seen['text_to_discuss']=='My own introduction.' and not seen['context_limits']['whole_section_supplied']
        assert len(json.dumps(seen,ensure_ascii=False))<22000
    asyncio.run(run())


def test_suggestions_require_selected_request_and_exact_unique_quote():
    invalid={**ADVICE,'suggestions':[{'quote':'My own introduction.','replacement':'My introduction.','reason':'Optional shorter wording.'}]}
    with pytest.raises(ValueError,match='without a selected'):validate_advice(invalid,'My own introduction.')
    assert validate_advice(invalid,'My own introduction.',True)['suggestions']
    with pytest.raises(ValueError,match='absent'):validate_advice(ADVICE,'Different words.')
    with pytest.raises(ValueError,match='more than one'):validate_advice(invalid,'My own introduction. My own introduction.',True)
    instruction=supervisor_instruction('connect','narrative')
    assert 'not a real supervisor' in instruction and 'Never rewrite the full section' in instruction
    assert 'process mining' not in instruction and 'never claim a supervisor' in instruction


def make_catalogue(app,pid):
    root=app.root(pid);root.mkdir(parents=True,exist_ok=True)
    resources=[{'id':'p2p-v1','title':'Old introduction','text':'A P2P example.','tags':['p2p','introduction'],'kind':'paragraph','version':'v1','locator':'lines 2–4'},
               {'id':'quote1','title':'Process mining evidence','text':'Exact source passage.','tags':['evidence'],'kind':'quotation','version':'2022','locator':'p. 276'}]
    path=root/'Passage catalogue.json';path.write_text(json.dumps({'schema':1,'resources':resources}))
    return path


def test_tags_search_and_sidecar_do_not_change_original_passages(desk):
    app,pid,sid=desk;path=make_catalogue(app,pid);original=path.read_bytes()
    result=app.resources(pid,tag='p2p',kind='paragraph',version='v1')
    assert result['total']==1 and result['resources'][0]['id']=='p2p-v1'
    changed=app.tag_resource(pid,'p2p-v1',{'base_hash':result['base_hash'],'tags':['p2p','business-objectives']})
    assert path.read_bytes()==original
    assert app.resources(pid,q='business-objectives')['total']==1
    with pytest.raises(Conflict):app.tag_resource(pid,'quote1',{'base_hash':result['base_hash'],'tags':['new']})
    changed2=app.tag_resource(pid,'quote1',{'base_hash':changed['base_hash'],'tags':['evidence','context']})
    assert changed2['base_hash']!=changed['base_hash']
    assert list((app.root(pid)/'Revisions').glob('*.md'))
    assert path.read_bytes()==original


def test_resource_facets_cover_all_entries_and_results_do_not_stop_at_200(desk):
    app,pid,sid=desk;root=app.root(pid);root.mkdir(parents=True,exist_ok=True)
    rows=[{'id':str(i),'title':'Passage '+str(i),'text':'Example.','tags':['p2p' if i<200 else 'late-tag'],
           'kind':'paragraph' if i<200 else 'quotation','version':'v1' if i<200 else 'v2'} for i in range(224)]
    (root/'Passage catalogue.json').write_text(json.dumps({'schema':1,'resources':rows}))
    result=app.resources(pid)
    assert len(result['resources'])==224 and result['total']==224 and not result['truncated']
    filtered=app.resources(pid,tag='p2p')
    assert len(filtered['resources'])==200 and filtered['versions']==['v1','v2']
    assert filtered['kinds']==['paragraph','quotation'] and 'late-tag' in filtered['tags']


def test_figures_reject_traversal_symlink_and_active_svg(desk,tmp_path):
    app,pid,sid=desk;root=app.root(pid)/'Figures';root.mkdir(parents=True)
    good=root/'outline.svg';good.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect width="2" height="2"/><text>Business requirements</text></svg>')
    assert app.figure(pid,'outline.svg')==good
    with pytest.raises(ValueError):app.figure(pid,'../outline.svg')
    bad=root/'active.svg';bad.write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
    with pytest.raises(ValueError):app.figure(pid,'active.svg')
    outside=tmp_path/'other.svg';outside.write_text(good.read_text());(root/'linked.svg').symlink_to(outside)
    with pytest.raises(ValueError):app.figure(pid,'linked.svg')


def test_polishing_prompt_is_local_and_excludes_old_children(desk):
    app,pid,sid=desk;save(app,pid,sid,{'Manuscript prose':'My own introduction.','Writing outline':'Evidence → interpretation.','Reasoning and decisions':'[citation needed]'})
    value=app.polishing_prompt(pid,sid)
    assert 'My own introduction.' in value['prompt'] and '[citation needed]' in value['prompt']
    assert 'Earlier child text.' not in value['prompt'] and 'Nothing is sent' in value['notice']
    assert not app.lab.tasks


def test_section_approval_requires_explicit_authority_and_current_hash(desk):
    app,pid,sid=desk;note=save(app,pid,sid,{'Manuscript prose':'My own introduction.'})
    with pytest.raises(ValueError,match='manuscript source'):app.complete(pid,sid,{'base_hash':note['hash']})
    note=save(app,pid,sid,{'Section manuscript source':'section'})
    with pytest.raises(Conflict):app.complete(pid,sid,{'base_hash':'stale'})
    completed=app.complete(pid,sid,{'base_hash':note['hash']})
    assert completed['writing_status']=='complete'
    assert latex_preview(app.ws,pid,{'section_ids':[sid]})['included'][0]['id']==sid


def test_restart_preserves_requests_without_automatically_running_them(desk):
    app,pid,sid=desk
    job={'id':'test-job','paper_id':pid,'section_id':sid,'status':'running','text':'Saved request text.',
         'text_hash':sha('Saved request text.'),'created':'2026-09-20T10:00:00Z'}
    app.store.set_setting('section_review:'+job['id'],job)
    app.recover()
    result=app.review_status(pid,sid,job['id'])
    assert result['status']=='interrupted' and not app.lab.tasks
    assert (app.root(pid)/'Reviews'/'test-job - Feedback.md').exists()


def test_http_contract_rejects_cross_origin_and_preserves_export_authority(tmp_path):
    from fastapi.testclient import TestClient
    from backend.main import create_app
    vault=tmp_path/'Vault';(vault/'.obsidian').mkdir(parents=True)
    app=create_app(data_dir=tmp_path/'data',vault_root=vault,auto_tutor=False)
    ws=app.state.lab.workspace;ws.configure(str(vault))
    plan=ws.create('Test paper','## Section: Introduction\n### Argument: Earlier argument')
    section=next(n for n in plan['nodes'] if n['type']=='section')
    section=ws.card(plan['id'],section['id'])
    section=ws.save(plan['id'],section['id'],section['hash'],{'Section manuscript source':'section','Manuscript prose':'My complete section.'})
    client=TestClient(app,base_url='http://127.0.0.1:8765',headers={'Origin':'http://127.0.0.1:8765'})
    base=f"/api/workspace/papers/{plan['id']}/sections/{section['id']}/writing"
    assert client.get(base).json()['section']['fields']['Manuscript prose']=='My complete section.'
    assert client.post(base+'/complete',json={'base_hash':section['hash']},headers={'Origin':'https://other.example'}).status_code==403
    assert client.post(base+'/complete',json={'base_hash':'stale'}).status_code==409
    assert client.post(base+'/complete',json={'base_hash':section['hash']}).json()['writing_status']=='complete'
    assert client.get(base+'/reviews').json()==[]
    assert 'My complete section.' in client.get(base+'/polishing-prompt').json()['prompt']
    assert client.post(base+'/review',json={'base_hash':section['hash'],'text':'x','question':'x','persona':'unregistered-supervisor'}).status_code==400


def test_model_requires_later_stage_selected_passage_and_deliberate_practice(desk,monkeypatch):
    from backend.writing_rounds import checkpoint
    import uuid
    async def run():
        app,pid,sid=desk
        first='The survey records visitors choosing exhibits. The records show which exhibits attract attention.'
        selected='These records show which exhibits attract attention, but they do not establish what visitors learned.'
        note=save(app,pid,sid,{'Manuscript prose':first})
        note=save(app,pid,sid,{'Manuscript prose':selected})
        body={'base_hash':note['hash'],'text':selected,'selected_text':selected,'question':'Show a short model after my tries.',
              'stage':'rewrite','request_demonstration':True}
        # Revisions/autosaves alone do not imply deliberate writing practice.
        assert app.writing(pid,sid)['practice']['meaningful_attempts']==0
        with pytest.raises(ValueError,match='first attempt'):await app.review(pid,sid,body)
        with pytest.raises(ValueError,match='Rewrite or Polish'):
            await app.review(pid,sid,{**body,'stage':'connect','prior_attempts_confirmed':True})
        with pytest.raises(ValueError,match='Select one to three'):
            await app.review(pid,sid,{**body,'selected_text':None,'prior_attempts_confirmed':True})
        seen={}
        async def generate(profile,payload,mode,model):
            if mode=='section_alignment_check':return supported_check(payload),{}
            assert mode=='section_rewrite'
            seen.update(payload)
            return edit_response('These records indicate which exhibits attract attention; they do not establish what visitors learned.',
                                 'The clauses contrast observed behaviour with the unmeasured outcome.'),{}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        # Work performed before this feature can be explicitly attested.
        job=await app.review(pid,sid,{**body,'prior_attempts_confirmed':True})
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert job['status']=='complete' and job['prior_attempts_confirmed']
        assert seen['allow_demonstration'] and job['context']['practice_evidence']['basis']=='author_attestation'
        assert app.section(pid,sid)['fields']['Manuscript prose']==selected
        assert app.review_status(pid,sid,job['id'])['context']['practice_evidence']['basis']=='author_attestation'
        # Intentional checkpoints travel in the vault and permit the same model
        # without an attestation on a second computer.
        note=save(app,pid,sid,{'Manuscript prose':first})
        checkpoint(app.ws,pid,sid,{'base_hash':note['hash'],'request_id':str(uuid.uuid4()),'reflection':'I introduced the observed evidence.','origin':'own_attempt'})
        note=save(app,pid,sid,{'Manuscript prose':selected})
        checkpoint(app.ws,pid,sid,{'base_hash':note['hash'],'request_id':str(uuid.uuid4()),'reflection':'I added the limit of the inference.','origin':'own_attempt'})
        job=await app.review(pid,sid,{**body,'base_hash':note['hash']})
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert job['status']=='complete' and job['context']['practice_evidence']['basis']=='recorded_checkpoints'
        assert job['context']['practice_evidence']['meaningful_attempts']==2
        assert len(list((app.root(pid)/'Reviews').glob('*.md')))==4
    asyncio.run(run())


def test_model_is_bounded_and_must_replace_exactly_the_selected_passage(desk,monkeypatch):
    from backend.section_writing import SectionAdvice,constrain_quotes
    async def run():
        app,pid,sid=desk;text='A word ' * 160
        note=save(app,pid,sid,{'Manuscript prose':text})
        with pytest.raises(ValueError,match='150 words'):
            await app.review(pid,sid,{'base_hash':note['hash'],'text':text,'selected_text':text,
                'question':'Model this.','stage':'rewrite','request_demonstration':True,'prior_attempts_confirmed':True})
        assert not app.lab.tasks
    asyncio.run(run())
    text='My own introduction.'
    schema=SectionAdvice.model_json_schema()
    constrain_quotes(schema,{'text_to_discuss':text,'allow_suggestions':True,'allow_demonstration':True})
    assert schema['properties']['suggestions']['maxItems']==1
    assert schema['properties']['suggestions']['minItems']==1 and 'suggestions' in schema['required']
    assert schema['$defs']['SectionSuggestion']['properties']['quote']['enum']==[text]
    invalid={**ADVICE,'suggestions':[{'quote':'own introduction','replacement':'A clear opening','reason':'A model.'}]}
    with pytest.raises(ValueError,match='selected passage'):validate_advice(invalid,text,True,True)
    invalid['suggestions'][0]['quote']=text
    invalid['suggestions'][0]['replacement']='word '*181
    with pytest.raises(ValueError,match='expanded'):validate_advice(invalid,text,True,True)


def test_identical_review_reuses_running_and_synced_completed_reading(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;note=save(app,pid,sid,{'Manuscript prose':'My own introduction.'})
        started=asyncio.Event();release=asyncio.Event();calls=[]
        check_calls=[]
        async def generate(profile,payload,mode,model):
            if mode=='section_alignment_check':
                check_calls.append(payload);return supported_check(payload),{}
            assert mode=='section_supervisor'
            calls.append(payload);started.set();await release.wait();return ADVICE,{}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        body={'base_hash':note['hash'],'text':'My own introduction.','question':'How can I connect these ideas?','check_advice':True}
        first=await app.review(pid,sid,body);await started.wait()
        running=await app.review(pid,sid,body)
        assert running['id']==first['id'] and running['reused'] and len(calls)==1
        release.set();await asyncio.gather(*list(app.lab.tasks.values()))
        completed=await app.review(pid,sid,body)
        assert completed['id']==first['id'] and completed['reused'] and not app.lab.tasks
        # The archive is the authority on another machine, not the old SQLite.
        app.store=Store(app.store.directory.parent/'other-data')
        app.store.set_setting('profile',{'provider':'ollama','model':'test-model','local_confirmed':True})
        restored=await app.review(pid,sid,body)
        assert restored['id']==first['id'] and restored['reused'] and len(calls)==1
        assert len(check_calls)==1
        # A saved metadata-only change does not invite another model judgement.
        note=save(app,pid,sid,{'Section manuscript source':'section'})
        body['base_hash']=note['hash']
        assert (await app.review(pid,sid,body))['id']==first['id']
        # A different actual question or meaning/context is a new reading.
        changed=await app.review(pid,sid,{**body,'question':'Is the actor identifiable?'})
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert changed['id']!=first['id'] and len(calls)==2
        note=save(app,pid,sid,{'Scope and boundaries':'Do not claim causality.'})
        scoped=await app.review(pid,sid,{**body,'base_hash':note['hash']})
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert scoped['id']!=first['id'] and len(calls)==3
        assert len(check_calls)==3
    asyncio.run(run())


def test_private_preferences_travel_with_paper_without_changing_manuscript(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;note=save(app,pid,sid,{'Manuscript prose':'My own introduction.'})
        root=app.root(pid);root.mkdir(parents=True,exist_ok=True)
        (root/'Coaching preferences.md').write_text('Ask one connecting question before polishing words.')
        seen=[]
        async def generate(profile,payload,mode,model):
            if mode=='section_alignment_check':return supported_check(payload),{}
            assert mode=='section_supervisor';seen.append(payload);return ADVICE,{}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        body={'base_hash':note['hash'],'text':'My own introduction.','question':'How can I connect these ideas?'}
        first=await app.review(pid,sid,body);await asyncio.gather(*list(app.lab.tasks.values()))
        assert seen[-1]['current_brief']['Private coaching preferences'].startswith('Ask one')
        (root/'Coaching preferences.md').write_text('Keep effective wording. '+'More context. '*160)
        second=await app.review(pid,sid,body);await asyncio.gather(*list(app.lab.tasks.values()))
        assert first['id']!=second['id']
        assert len(seen[-1]['current_brief']['Private coaching preferences'])==1500
        assert 'Private coaching preferences' in seen[-1]['context_limits']['shortened_fields']
        assert app.section(pid,sid)['hash']==note['hash']
    asyncio.run(run())


def test_alignment_phase_exposes_only_reading_and_keeps_editor_independent(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;original='My own introduction.'
        moves=[{'id':'observations','title':'Introduce the observations','points':['Name what was recorded.']},
               {'id':'interpretation','title':'Explain interpretation','points':['Relate observations to the question.']}]
        note=save(app,pid,sid,{'Manuscript prose':original,'Section writing plan':json.dumps(moves)})
        checking=asyncio.Event();release=asyncio.Event();packets=[]
        raw=edit_response('My introduction.')
        proposal=rewrite_advice(raw,original)
        async def generate(profile,payload,mode,model):
            if mode=='section_rewrite':return raw,{'model':'first-reading'}
            assert mode=='section_alignment_check'
            packets.append(payload);checking.set();await release.wait()
            return supported_check(payload),{'model':'bounded-check'}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{'base_hash':note['hash'],'text':original,'selected_text':original,
                                     'question':'Can this wording be shorter?','request_suggestions':True,
                                     'stage':'rewrite','move_id':'observations'})
        await asyncio.wait_for(checking.wait(),2)
        try:
            current=app.review_status(pid,sid,job['id'])
            assert current['status']=='running' and current['phase']=='checking'
            assert current['result'] is None
            assert set(current['provisional'])=={'reading','strengths'}
            assert 'priorities' not in current['provisional'] and 'suggestions' not in current['provisional']
            # A writer can change both prose and outline while the second call
            # reads the first saved version. No review is allowed to restore it.
            save(app,pid,sid,{'Manuscript prose':'My new draft written while the check runs.',
                             'Section writing plan':json.dumps([{'id':'new-role','title':'A revised outline role'}])})
        finally:
            release.set();await asyncio.gather(*list(app.lab.tasks.values()))
        result=app.review_status(pid,sid,job['id'])
        assert result['status']=='complete' and result['phase']=='complete'
        assert result['result']==proposal
        assert result['alignment']['original_result']==proposal
        assert result['check_provenance']['model']=='bounded-check'
        assert packets[0]['frozen_context']['text_to_discuss']==original
        assert 'outline_focus' not in packets[0]['frozen_context']
        assert result['context']['outline_focus']['selected']['id']=='observations'
        assert app.section(pid,sid)['fields']['Manuscript prose']=='My new draft written while the check runs.'
    asyncio.run(run())


def test_unsupported_advice_and_next_question_are_withheld_and_archived(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;original='My own introduction.'
        note=save(app,pid,sid,{'Manuscript prose':original})
        raw=edit_response('An introduction with an invented result.','Added detail.')
        proposal=rewrite_advice(raw,original)
        calls=[]
        async def generate(profile,payload,mode,model):
            calls.append(mode)
            if mode=='section_rewrite':return raw,{}
            assert mode=='section_alignment_check'
            return {'decisions':[{'id':item['id'],'verdict':'unsupported','reason':'This advice invents a requirement or content.'}
                                  for item in payload['items']]},{}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{'base_hash':note['hash'],'text':original,'selected_text':original,
                                     'question':'Suggest shorter wording.','request_suggestions':True})
        await asyncio.gather(*list(app.lab.tasks.values()))
        result=app.review_status(pid,sid,job['id'])
        assert calls==['section_rewrite','section_alignment_check']
        assert result['status']=='complete'
        assert result['result']['priorities']==result['result']['suggestions']==[]
        assert result['result']['next_question']=='Continue with the next idea in your outline; keep wording that works.'
        assert result['alignment']['withheld_count']==2
        assert result['alignment']['original_result']==proposal
        assert app.section(pid,sid)['hash']==note['hash']
        # The exact proposed criticism remains private and reviewable after sync.
        app.store=Store(app.store.directory.parent/'restored-data')
        restored=app.review_status(pid,sid,job['id'])
        assert restored['alignment']['original_result']==proposal
        assert restored['result']==result['result']
    asyncio.run(run())


def test_unavailable_alignment_check_preserves_draft_and_original_advice(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;note=save(app,pid,sid,{'Manuscript prose':'My own introduction.'})
        calls=[]
        async def generate(profile,payload,mode,model):
            calls.append(mode)
            if mode=='section_supervisor':return ADVICE,{'model':'first-reading'}
            assert mode=='section_alignment_check'
            raise ValueError('Local checker timed out.')
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{'base_hash':note['hash'],'text':'My own introduction.','question':'Read this connection.','check_advice':True})
        await asyncio.gather(*list(app.lab.tasks.values()))
        result=app.review_status(pid,sid,job['id'])
        assert calls==['section_supervisor','section_alignment_check']
        assert result['status']=='complete' and result['alignment']['status']=='unavailable'
        assert result['result']['priorities']==[]
        assert result['result']['next_question']=='Continue with the next idea in your outline; keep wording that works.'
        assert result['alignment']['original_result']==ADVICE
        assert result['alignment']['error']=='Local checker timed out.'
        assert app.section(pid,sid)['hash']==note['hash'] and not app.lab.tasks
        saved=(app.root(pid)/'Reviews'/(job['id']+' - Feedback.md')).read_text()
        assert 'Local checker timed out.' in saved and 'original_result' in saved
    asyncio.run(run())


def test_arbitrary_basis_is_rejected_before_checker(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;note=save(app,pid,sid,{'Manuscript prose':'My own introduction.'})
        invalid={**ADVICE,'priorities':[{**ADVICE['priorities'][0],'basis_id':'invented-supervisor-approval'}]}
        calls=[]
        async def generate(profile,payload,mode,model):
            calls.append(mode)
            return invalid,{}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{'base_hash':note['hash'],'text':'My own introduction.','question':'Read this connection.'})
        await asyncio.gather(*list(app.lab.tasks.values()))
        result=app.review_status(pid,sid,job['id'])
        assert calls==['section_supervisor']
        assert result['status']=='failed' and result['result'] is None
        assert 'guidance absent' in result['error']
        assert app.section(pid,sid)['hash']==note['hash']
    asyncio.run(run())


def test_conflicting_current_guidance_stops_before_any_model_call(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;note=save(app,pid,sid,{'Manuscript prose':'My own introduction.'})
        root=app.root(pid);root.mkdir(parents=True,exist_ok=True)
        source='P0001 Keep the description in past tense.\nP0002 Keep the description in present tense.\n'
        (root/'Discussion.txt').write_text(source)
        requirements=[]
        for ident,other,paragraph,quote in [
            ('past-tense','present-tense','P0001','Keep the description in past tense.'),
            ('present-tense','past-tense','P0002','Keep the description in present tense.')]:
            requirements.append({'id':ident,'instruction':quote,'stage':['connect'],'scope':{'section_id':sid},
                'status':'active','conflicts_with':[other],
                'evidence':[{'source_id':'discussion','paragraphs':[paragraph],'quote':quote}]})
        (root/'Tutor knowledge.md').write_text('```json\n'+json.dumps({'schema_version':1,
            'source_documents':[{'id':'discussion','title':'Generic discussion','path':'Discussion.txt','sha256':sha(source)}],
            'requirements':requirements})+'\n```\n')
        calls=[]
        async def generate(*args):
            calls.append(args)
            raise AssertionError('A conflict must not trigger model inference.')
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{'base_hash':note['hash'],'text':'My own introduction.','question':'Read this connection.'})
        await asyncio.gather(*list(app.lab.tasks.values()))
        result=app.review_status(pid,sid,job['id'])
        assert calls==[] and result['status']=='complete'
        assert result['alignment']['status']=='guidance_conflict'
        assert result['context']['grounding']['conflicts']==[['past-tense','present-tense']]
        assert result['result']['priorities']==result['result']['suggestions']==[]
        assert 'conflicting guidance' in result['result']['next_question']
        assert app.section(pid,sid)['hash']==note['hash']
    asyncio.run(run())


def test_changed_alignment_instruction_invalidates_review_cache(desk,monkeypatch):
    from backend import alignment_check
    async def run():
        app,pid,sid=desk;note=save(app,pid,sid,{'Manuscript prose':'My own introduction.'})
        calls=[]
        async def generate(profile,payload,mode,model):
            calls.append(mode)
            if mode=='section_alignment_check':return supported_check(payload),{}
            return ADVICE,{}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        body={'base_hash':note['hash'],'text':'My own introduction.','question':'Read this connection.','check_advice':True}
        first=await app.review(pid,sid,body)
        await asyncio.gather(*list(app.lab.tasks.values()))
        reused=await app.review(pid,sid,body)
        assert reused['id']==first['id'] and reused['reused']
        changed_instruction=alignment_check.CHECK_INSTRUCTION+'\nA changed evaluation contract.'
        monkeypatch.setattr(alignment_check,'CHECK_INSTRUCTION',changed_instruction)
        monkeypatch.setattr('backend.section_writing.CHECK_INSTRUCTION',changed_instruction)
        fresh=await app.review(pid,sid,body)
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert fresh['id']!=first['id'] and fresh['request_fingerprint']!=first['request_fingerprint']
        assert calls==['section_supervisor','section_alignment_check']*2
    asyncio.run(run())


def test_next_only_advice_also_gets_checked(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;note=save(app,pid,sid,{'Manuscript prose':'My own introduction.'})
        proposal={**ADVICE,'priorities':[],'strengths':[],'next_question':'Why is the present connection missing?'}
        calls=[]
        async def generate(profile,payload,mode,model):
            calls.append(mode)
            if mode=='section_supervisor':return proposal,{}
            assert [item['id'] for item in payload['items']]==['next-0']
            return {'decisions':[{'id':'next-0','verdict':'unsupported','reason':'It asks for a link that is already present.'}]},{}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{'base_hash':note['hash'],'text':'My own introduction.','question':'Can I continue?','check_advice':True})
        await asyncio.gather(*list(app.lab.tasks.values()))
        result=app.review_status(pid,sid,job['id'])
        assert calls==['section_supervisor','section_alignment_check']
        assert result['alignment']['status']=='checked'
        assert result['result']['priorities']==[] and result['result']['suggestions']==[]
        assert result['result']['next_question']=='Continue with the next idea in your outline; keep wording that works.'
        assert result['alignment']['original_result']==proposal
    asyncio.run(run())


def test_ordinary_reading_uses_one_call_and_comparison_is_explicit_and_cache_distinct(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;note=save(app,pid,sid,{'Manuscript prose':'My own introduction.'})
        calls=[]
        async def generate(profile,payload,mode,model):
            calls.append(mode)
            if mode=='section_alignment_check':return supported_check(payload),{}
            assert mode=='section_supervisor';return ADVICE,{'model':'first-reading'}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        body={'base_hash':note['hash'],'text':'My own introduction.','question':'What does this passage convey?'}
        ordinary=await app.review(pid,sid,body)
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert calls==['section_supervisor']
        assert ordinary['alignment']['status']=='not_requested'
        assert ordinary['result']==ADVICE and ordinary['check_provenance'] is None
        assert 'provisional' not in ordinary and ordinary['phase']=='complete'
        assert ordinary['model_context']['compare_advice'] is False
        compared=await app.review(pid,sid,{**body,'check_advice':True})
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert compared['id']!=ordinary['id'] and compared['request_fingerprint']!=ordinary['request_fingerprint']
        assert calls==['section_supervisor','section_supervisor','section_alignment_check']
        assert compared['alignment']['status']=='checked'
        assert compared['model_context']['compare_advice'] is True
        reused=await app.review(pid,sid,{**body,'check_advice':True})
        assert reused['id']==compared['id'] and reused['reused']
        assert len(calls)==3
        assert app.section(pid,sid)['hash']==note['hash']
    asyncio.run(run())


def test_requested_replacement_always_runs_comparison_even_when_checkbox_off(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;text='My own introduction.'
        note=save(app,pid,sid,{'Manuscript prose':text})
        raw=edit_response('My introduction.','Optional shorter wording.')
        proposal=rewrite_advice(raw,text)
        calls=[]
        async def generate(profile,payload,mode,model):
            calls.append(mode)
            if mode=='section_alignment_check':return supported_check(payload),{}
            return raw,{}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{'base_hash':note['hash'],'text':text,'selected_text':text,
                                     'question':'Suggest shorter wording.','request_suggestions':True,'check_advice':False})
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert calls==['section_rewrite','section_alignment_check']
        assert job['context']['compare_advice'] is False and job['context']['allow_suggestions'] is True
        assert job['alignment']['status']=='checked' and job['result']==proposal
        assert app.section(pid,sid)['hash']==note['hash']
    asyncio.run(run())


def test_next_step_intent_does_not_accept_model_criticism(desk,monkeypatch):
    from backend.section_writing import SectionAdvice,constrain_quotes
    from backend.coaching_context import model_packet
    async def run():
        app,pid,sid=desk;note=save(app,pid,sid,{'Manuscript prose':'My own introduction.'})
        async def generate(profile,payload,mode,model):return ADVICE,{}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{'base_hash':note['hash'],'text':'My own introduction.',
            'question':'What should I write next?','review_intent':'next_step'})
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert job['status']=='failed' and 'next writing step' in job['error']
        assert app.section(pid,sid)['hash']==note['hash']
        schema=SectionAdvice.model_json_schema();constrain_quotes(schema,model_packet(job['context']))
        assert schema['properties']['priorities']['maxItems']==0
        assert schema['properties']['suggestions']['maxItems']==0
    asyncio.run(run())


def test_compact_rewrite_can_keep_or_ask_without_inventing_a_change():
    text='The evidence may indicate a delay [].'
    keep=rewrite_advice({'decision':'keep','replacement':text,'explanation':'This is already concise.','clarification':''},text)
    assert keep['suggestions']==[] and keep['priorities']==[] and keep['edit_decision']=='keep'
    clarify=rewrite_advice({'decision':'clarify','replacement':'','explanation':'The referent is unresolved.','clarification':'Does “it” refer to the event or the trace?'},text)
    assert clarify['suggestions']==[] and clarify['next_question'].startswith('Does')
    with pytest.raises(ValueError):rewrite_advice({'decision':'keep','replacement':'Changed claim.','explanation':'Clearer.','clarification':''},text)
    with pytest.raises(ValueError):rewrite_advice({'decision':'clarify','replacement':'Invented meaning.','explanation':'A choice.','clarification':'Which?'},text)
    with pytest.raises(ValueError):rewrite_advice({'decision':'edit','replacement':'','explanation':'A choice.','clarification':''},text)


def test_new_retrieval_query_does_not_import_future_outline_points(desk,monkeypatch):
    from backend.section_writing import SectionReviewRequest
    app,pid,sid=desk
    move={'id':'opening','title':'Opening','points':['A distinct future requirement.']}
    note=save(app,pid,sid,{'Section writing plan':json.dumps([move])})
    seen={}
    def retrieve(*args,**kwargs):
        seen['query']=args[4]
        return {'available':False,'requirements':[],'general_bases':[],'conflicts':[],'notices':[]}
    monkeypatch.setattr('backend.section_writing.tutor_grounding.retrieve',retrieve)
    app._payload(note,app.ws.get(pid),SectionReviewRequest(base_hash=note['hash'],text='The evidence is clear.',
        question='Is the reference clear?',move_id='opening'))
    assert seen['query']=='Is the reference clear? The evidence is clear.'
    assert 'future requirement' not in seen['query']


@pytest.mark.parametrize('provider',['ollama','lmstudio'])
@pytest.mark.parametrize('mode',['section_rewrite','section_rewrite_repair'])
def test_compact_edit_provider_dispatch_uses_its_own_schema_and_provenance(monkeypatch,provider,mode):
    from unittest.mock import AsyncMock
    import httpx
    from backend import providers
    from backend.section_writing import SectionRewrite,REWRITE_INSTRUCTION,REPAIR_INSTRUCTION
    monkeypatch.setattr(providers,'model_inventory',AsyncMock(return_value={'models':[{'id':'qwen3:8b','digest':'local-test'}]}))
    original=httpx.AsyncClient;seen={}
    response=edit_response('To answer this question, we use the data [].','Removed a redundant introductory phrase.')
    def respond(request):
        seen.update(json.loads(request.content))
        data=({'message':{'content':json.dumps(response)},'done':True,'done_reason':'stop'} if provider=='ollama'
              else {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(response)}}]})
        return httpx.Response(200,json=data)
    monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    payload={'task':'selected_passage_edit','text_to_discuss':'In order to answer this question, we use the data [].',
             'writer_question':'Make the opening shorter, keeping the meaning.','surrounding_draft':{},'source_conflicts':[]}
    result,provenance=asyncio.run(providers.generate({'provider':provider,'model':'qwen3:8b','local_confirmed':True},payload,mode,SectionRewrite))
    version='section-edit-repair-1' if mode=='section_rewrite_repair' else 'section-edit-1'
    assert result==response and provenance['prompt_version']==version
    assert provenance['schema_version']==version and provenance['model_digest']=='local-test'
    instruction=REWRITE_INSTRUCTION+('\n'+REPAIR_INSTRUCTION if mode=='section_rewrite_repair' else '')
    assert seen['messages'][0]['content']==instruction
    schema=seen['format'] if provider=='ollama' else seen['response_format']['json_schema']['schema']
    assert set(schema['properties'])=={'decision','replacement','explanation','clarification'}
    assert 'priorities' not in json.dumps(schema)


def test_requested_edit_repairs_one_external_contract_failure_before_comparison(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;text='The records can suggest a direction [].'
        note=save(app,pid,sid,{'Manuscript prose':text})
        modes=[];packets=[]
        async def generate(profile,payload,mode,model):
            modes.append(mode);packets.append(payload)
            if mode=='section_rewrite':return edit_response('The records suggest a direction [].'),{'model':'first'}
            if mode=='section_rewrite_repair':return edit_response('A direction can be suggested by the records [].'),{'model':'repair'}
            assert mode=='section_alignment_check'
            return supported_check(payload),{'model':'comparison'}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{'base_hash':note['hash'],'text':text,'selected_text':text,
            'question':'Suggest a clearer sentence.','request_suggestions':True})
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert modes==['section_rewrite','section_rewrite_repair','section_alignment_check']
        assert packets[1]['repair_constraints']['original_spans_to_keep']==['can']
        assert job['repair_attempted'] and len(job['edit_attempts'])==2
        assert job['edit_attempts'][0]['raw']['replacement']=='The records suggest a direction [].'
        assert job['edit_attempts'][0]['flags'][0]['code']=='weak_modal_removed'
        assert job['edit_attempts'][1]['flags']==[]
        assert job['result']['suggestions'][0]['replacement']=='A direction can be suggested by the records [].'
        assert app.section(pid,sid)['hash']==note['hash']
        app.store=Store(app.store.directory.parent/'restored-edit-traces')
        assert app.review_status(pid,sid,job['id'])['edit_attempts']==job['edit_attempts']
    asyncio.run(run())


@pytest.mark.parametrize('repair_result',['violates','different_modal','error'])
def test_failed_edit_repair_never_loops_or_calls_comparison(desk,monkeypatch,repair_result):
    async def run():
        app,pid,sid=desk;text='The records can suggest a direction [].'
        note=save(app,pid,sid,{'Manuscript prose':text})
        modes=[]
        async def generate(profile,payload,mode,model):
            modes.append(mode)
            assert mode in ('section_rewrite','section_rewrite_repair')
            if mode=='section_rewrite_repair':
                if repair_result=='error':raise ValueError('Repair runtime unavailable.')
                if repair_result=='different_modal':return edit_response('The records may suggest a direction [].'),{}
            return edit_response('The records suggest a direction [].'),{}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{'base_hash':note['hash'],'text':text,'selected_text':text,
            'question':'Shorten the wording.','request_suggestions':True})
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert modes==['section_rewrite','section_rewrite_repair']
        assert job['status']=='complete' and job['result']['suggestions']==[]
        assert 'No replacement' in job['result']['reading'] and job['check_provenance'] is None
        assert len(job['edit_attempts'])==2
        if repair_result=='error':assert job['edit_attempts'][1]['error']=='Repair runtime unavailable.'
        else:assert job['edit_attempts'][1]['flags']
        assert app.section(pid,sid)['hash']==note['hash']
    asyncio.run(run())


def test_semantic_comparison_rejection_does_not_start_edit_repair(desk,monkeypatch):
    async def run():
        app,pid,sid=desk;text='The records show a pattern.'
        note=save(app,pid,sid,{'Manuscript prose':text})
        modes=[]
        async def generate(profile,payload,mode,model):
            modes.append(mode)
            if mode=='section_rewrite':return edit_response('The records explain a pattern.'),{}
            assert mode=='section_alignment_check'
            return {'decisions':[{'id':item['id'],'verdict':'unsupported','reason':'Showing and explaining make different claims.'} for item in payload['items']]},{}
        monkeypatch.setattr('backend.section_writing.providers.generate',generate)
        job=await app.review(pid,sid,{'base_hash':note['hash'],'text':text,'selected_text':text,
            'question':'Make the wording clearer.','request_suggestions':True})
        await asyncio.gather(*list(app.lab.tasks.values()))
        assert modes==['section_rewrite','section_alignment_check']
        assert len(job['edit_attempts'])==1 and not job.get('repair_attempted')
        assert job['result']['suggestions']==[]
    asyncio.run(run())
