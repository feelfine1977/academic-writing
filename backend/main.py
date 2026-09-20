"""Loopback-only API; source notes are read, learner work is stored separately."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
import asyncio
import io
import json
import os
import secrets
import sqlite3
import zipfile
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from starlette.concurrency import run_in_threadpool
import base64
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from .storage import Store, now, uid, validate_backup
from .content import import_pack, public_exercise, import_source, safe_source, build_pack, SKILLS
from .service import Lab, DEFAULT_PROFILE
from .obsidian import Companion
from . import providers
from .workspace import Workspace, Conflict

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_VAULT=ROOT/'data'/'vault-not-configured'

class Body(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Submit(Body):
    exercise_key:str
    text:str=Field(min_length=1,max_length=12000)
    request_key:str=Field(min_length=1,max_length=200)
    session_id:str|None=None
    outline:str|None=Field(default=None,max_length=8000)
    reason:str=Field(default='',max_length=2500)
    values:list[str]|None=None
    base_version:int|None=None
    request_feedback:bool=False

class SessionBody(Body):
    exercise_key:str
    fresh:bool=False

class DraftBody(Body):
    text:str=Field(max_length=12000)
    outline:str=Field(default='',max_length=8000)
    base_version:int

class Assistance(Body):
    session_id:str
    kind:Literal['hint','example']

class ReviewBody(Body):
    attempt_id:str
    kind:Literal['initial_hint','review_revision','argument_review','show_example']='initial_hint'
    request_key:str=Field(min_length=1,max_length=200)

class TeachingView(Body):
    session_id:str

class WordingFlag(Body):
    context:str=Field(min_length=1,max_length=500)
    quote:str=Field(default='',max_length=4000)
    comment:str=Field(min_length=1,max_length=4000)

class FlagStatus(Body):
    status:Literal['open','resolved']

class CompletionReview(Body):
    attempt_id:str
    reflection:str=Field(min_length=10,max_length=2500)

class CompanionModule(Body):
    module_id:str=Field(min_length=1,max_length=150)

class CompanionSelection(Body):
    note_id:str=Field(min_length=1,max_length=50)
    file_hash:str=Field(pattern=r'^[a-f0-9]{64}$')

class CompanionImport(Body):
    selected:list[CompanionSelection]=Field(min_length=1,max_length=30)

class Profile(Body):
    provider:Literal['ollama','lmstudio']
    model:str=Field(max_length=250)
    language:Literal['en','de','pl']='en'
    local_confirmed:bool=True
    review_mode:Literal['careful','quick']='careful'
    verifier_model:str=Field(default='',max_length=250)
    structure_model:str=Field(default='',max_length=250)

class Build(Body):
    title:str=Field(min_length=1,max_length=180)
    outline:str=Field(min_length=10,max_length=6000)
    source_ids:list[str]=Field(default_factory=list,max_length=5)
    skill:Literal['S03']='S03'
    confirmed:bool
    paragraph_only:bool=False

class PaperSelection(Body):
    base_version:int
    attempt_id:str|None=None
    source_ids:list[str]|None=Field(default=None,max_length=12)
    confirmed:bool=False
    clear_selection:bool=False

class WritingQuestion(Body):
    exercise_key:str
    node_id:str|None=None
    text:str=Field(min_length=1,max_length=12000)
    question:str=Field(min_length=1,max_length=1500)
    before:str=Field(default="",max_length=700)
    after:str=Field(default="",max_length=700)
    full_text:str|None=Field(default=None,max_length=12000)
    selection_start:int|None=Field(default=None,ge=0,le=24000)
    outline:str|None=Field(default=None,max_length=8000)
    review_focus:Literal['general','evidence','structure']='general'

class WordRequest(Body):
    node_id:str
    selected:str=Field(min_length=1,max_length=160)
    before:str=Field(default="",max_length=700)
    after:str=Field(default="",max_length=700)

class ArgumentPlan(Body):
    scratchpad:str|None=Field(default=None,max_length=3000)
    base_version:int
    reader_before:str|None=Field(default=None,max_length=3000)
    contribution:str|None=Field(default=None,max_length=3000)
    bridge:str|None=Field(default=None,max_length=3000)
    handover:str|None=Field(default=None,max_length=3000)
    open_question:str|None=Field(default=None,max_length=3000)
    next_action:str|None=Field(default=None,max_length=3000)

class ArgumentOrder(Body):
    base_version:int
    node_ids:list[str]=Field(max_length=49)

class ApplyOrder(Body):
    base_version:int

class ReverseOutline(Body):
    base_version:int
    synopsis:str=Field(max_length=1000)

class EvidenceRecord(Body):
    base_version:int
    node_ids:list[str]=Field(min_length=1,max_length=12)
    claim:str=Field(min_length=1,max_length=3000)
    locator:str=Field(default='',max_length=2000)
    rationale:str=Field(default='',max_length=3000)
    boundary:str=Field(default='',max_length=2000)
    status:Literal['open_question','linked_unassessed','supports','supports_narrower','does_not_support']='open_question'

class RevisionDecision(Body):
    base_version:int=Field(ge=0)
    text:str=Field(min_length=1,max_length=4000)
    status:Literal['proposed','confirmed','needs_clarification','resolved','superseded']='proposed'
    node_ids:list[str]=Field(min_length=1,max_length=49)
    document_id:str|None=None
    segment_id:str|None=None
    quote:str=Field(default='',max_length=4000)

class PassagePlacement(Body):
    base_version:int=Field(ge=0)
    document_id:str
    segment_id:str
    node_id:str
    fit:Literal['direct','slight_changes','rebuild','reserve']
    reason:str=Field(min_length=1,max_length=3000)

class PassageReuse(Body):
    base_version:int=Field(ge=0)
    document_id:str
    segment_ids:list[str]=Field(min_length=1,max_length=8)
    text:str=Field(default='',max_length=12000)
    mode:Literal['keep','adapt']='keep'
    reason:str=Field(default='',max_length=3000)
    confirmed:bool=False

class PassageSearch(Body):
    document_id:str
    node_id:str
    q:str=Field(default='',max_length=500)
    colour:Literal['all','agreed','needs_review']='all'
    include_structure:bool=False

class FocusSession(Body):
    id:str=Field(pattern=r'^[a-zA-Z0-9-]{1,80}$')
    goal:str=Field(default='',max_length=500)
    next_action:str=Field(default='',max_length=1000)
    parked:str=Field(default='',max_length=3000)
    route:str=Field(default='',max_length=500)
    started:str=Field(max_length=60)
    finished:str=Field(max_length=60)
    minutes:int=Field(ge=1,le=120)
    outcome:Literal['interval_elapsed','stopped_early']

def create_app(data_dir=None,vault_root=None,auto_tutor=True):
    store=Store(data_dir or os.getenv('AWL_DATA_DIR',ROOT/'data'))
    try:local_paths=json.loads((store.directory/'local-settings.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):local_paths={}
    lab=Lab(store,ROOT,vault_root or os.getenv('AWL_VAULT') or local_paths.get('vault') or DEFAULT_VAULT)
    lab.seed()
    from .fiction import Fiction, router as fiction_router
    fiction=Fiction(lab)
    lab.workspace=Workspace(lab)
    from .section_writing import SectionWriting
    section_writing=SectionWriting(lab)
    from .voice_notes import VoiceNotes, voice_router
    voice_notes=VoiceNotes(lab)
    from .workspace_sources import PaperSources
    paper_sources=PaperSources(lab.workspace)
    from .literature import Literature
    literature=Literature(lab.workspace)
    from .reading import Reading, router as reading_router
    reading=Reading(lab,literature)
    from .planner import Planner, router as planner_router
    planner=Planner(lab.workspace)
    from .learning_sync import LearningSync
    learning_sync=LearningSync(lab.workspace)
    companion=Companion(lab)
    token=secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app):
        section_writing.recover()
        voice_notes.recover()
        fiction.recover()
        reading.recover()
        store.execute("UPDATE jobs SET status='interrupted',error='The app restarted. Your attempt is saved; request feedback again.' WHERE status IN ('queued','running')")
        if auto_tutor and not store.setting('profile',{}).get('model'):
            inventory=await providers.model_inventory('ollama')
            for name in ('qwen3:8b','llama3.1:8b'):
                if name in [m['id'] for m in inventory['models']]:
                    store.set_setting('profile',{'provider':'ollama','model':name,'language':'en','local_confirmed':True})
                    break
        async def share_learning():
            while True:
                await run_in_threadpool(learning_sync.sync)
                await asyncio.sleep(15)
        sync_task=asyncio.create_task(share_learning())
        async def receive_ipad_reading():
            while True:
                try: await reading.process_ipad_requests()
                except (ValueError,OSError): pass  # A disconnected vault can be selected again.
                await asyncio.sleep(15)
        reading_sync_task=asyncio.create_task(receive_ipad_reading())
        try:yield
        finally:
            reading_sync_task.cancel()
            try: await reading_sync_task
            except asyncio.CancelledError: pass
            await voice_notes.close()
            await fiction.close()
            await reading.close()
            sync_task.cancel()
            try:await sync_task
            except asyncio.CancelledError:pass
            await lab.close()
            await run_in_threadpool(learning_sync.sync)

    app=FastAPI(title='Writing Lab',docs_url=None,redoc_url=None,lifespan=lifespan)
    app.state.lab=lab;app.state.store=store
    app.state.section_writing=section_writing
    app.state.voice_notes=voice_notes
    app.include_router(voice_router(voice_notes))
    app.state.fiction=fiction
    app.include_router(fiction_router(fiction,ROOT))
    app.state.reading=reading
    app.include_router(reading_router(reading))
    app.state.planner=planner
    app.include_router(planner_router(planner))

    @app.middleware('http')
    async def local_only(request,call_next):
        host=request.headers.get('host','')
        try:allowed=urlsplit('http://'+host).hostname in {'127.0.0.1','localhost','::1'}
        except ValueError:allowed=False
        if not allowed:return JSONResponse({'detail':'Only loopback access is allowed.'},status_code=403)
        origin=request.headers.get('origin')
        if origin and origin not in {'http://'+host,'https://'+host}:
            return JSONResponse({'detail':'Cross-origin access is blocked.'},status_code=403)
        if request.method not in ('GET','HEAD','OPTIONS') and not origin and request.headers.get('x-awl-token')!=token:
            return JSONResponse({'detail':'Reload the app to renew its local access token.'},status_code=403)
        if request.method in ('POST','PUT','PATCH'):
            limit=250_000_000 if request.url.path.startswith('/api/restore') else 25_000_000
            if request.url.path.startswith('/api/workspace/papers/') and request.url.path.endswith('/voice-notes'):
                limit=40_100_000
            if len(await request.body())>limit:return JSONResponse({'detail':f'Request too large ({limit//1_000_000} MB maximum).'},status_code=413)
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        if '/section-writing/figures/' in request.url.path:
            response.headers['Content-Security-Policy']="default-src 'none'; style-src 'unsafe-inline'; sandbox; frame-ancestors 'none'"
        return response

    @app.exception_handler(ValueError)
    async def value_error(request,error):return JSONResponse({'detail':str(error)},status_code=400)

    @app.exception_handler(Conflict)
    async def workspace_conflict(request,error):return JSONResponse({'detail':str(error),**error.details},status_code=409)

    @app.get('/api/workspace')
    def workspace_catalogue():return {**lab.workspace.catalogue(),'learning_sync':learning_sync.last}

    @app.post('/api/workspace/sync')
    def workspace_sync():return learning_sync.sync()

    @app.post('/api/workspace/configure')
    def workspace_configure(body:dict):
        if set(body)!={'vault'} or not isinstance(body['vault'],str):raise ValueError('Supply the local vault folder path.')
        result=lab.workspace.configure(body['vault'])
        from .paper import Paper
        from .teaching import Teaching
        from .assets import load
        lab.paper=Paper(store,ROOT,lab.vault);lab.teaching=Teaching(lab)
        lab.materials=load(ROOT,'tutor_materials.json',{'version':1,'references':[],'exercises':{}},lab.vault)
        return result

    @app.post('/api/workspace/open-folder')
    def workspace_open_folder(body:dict):
        if not isinstance(body.get('folder'),str):raise ValueError('Supply a paper folder inside your vault.')
        return lab.workspace.open_folder(body['folder'])

    @app.post('/api/workspace/migrate-wise')
    def workspace_migrate_wise():
        from .legacy_migration import LegacyMigration
        return LegacyMigration(lab).run()

    @app.post('/api/workspace/papers')
    def workspace_create(body:dict):
        if set(body)-{'title','outline'} or not isinstance(body.get('title'),str) or not isinstance(body.get('outline',''),str):raise ValueError('Supply a title and optional outline.')
        if len(body['title'])>150 or len(body.get('outline',''))>200000:raise ValueError('The title or outline is too long.')
        return lab.workspace.create(body['title'],body.get('outline',''))

    @app.get('/api/workspace/paper-template')
    def workspace_paper_template(title:str,key:str):
        from urllib.parse import quote
        from .workspace_templates import paper_template
        raw,filename=paper_template(title,key,[p['id'] for p in lab.workspace.catalogue()['papers']])
        return Response(raw,media_type='application/zip',headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(filename)})

    @app.get('/api/workspace/manual-paper-guide')
    def workspace_manual_paper_guide():
        return FileResponse(ROOT/'templates'/'manual-paper'/'START_HERE.md',media_type='text/plain')

    @app.get('/api/workspace/section-writing-guide')
    def workspace_section_writing_guide():
        return FileResponse(ROOT/'templates'/'section-writing'/'START_HERE.md',media_type='text/plain')

    @app.get('/api/workspace/section-template')
    def workspace_section_template():
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for filename in ('Section.md','START_HERE.md','Tutor knowledge.md'):
                archive.write(ROOT/'templates'/'section-writing'/filename,arcname=filename)
        return Response(output.getvalue(),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="Section writing template.zip"'})

    @app.get('/api/workspace/papers/{id}')
    def workspace_paper(id:str):return lab.workspace.get(id)

    @app.get('/api/workspace/papers/{id}/sections/{section_id}/writing')
    def section_workspace(id:str,section_id:str):return section_writing.writing(id,section_id)

    @app.get('/api/workspace/papers/{id}/sections/{section_id}/writing/guidance')
    def section_guidance(id:str,section_id:str,stage:str='connect',move_id:str|None=None):
        if stage not in ('connect','rewrite','polish'):raise ValueError('Choose a writing stage.')
        return section_writing.guidance(id,section_id,stage,move_id)

    @app.post('/api/workspace/papers/{id}/sections/{section_id}/writing/review')
    async def section_review(id:str,section_id:str,body:dict):return await section_writing.review(id,section_id,body)

    @app.post('/api/workspace/papers/{id}/sections/{section_id}/writing/complete')
    def section_complete(id:str,section_id:str,body:dict):return section_writing.complete(id,section_id,body)

    @app.get('/api/workspace/papers/{id}/sections/{section_id}/writing/practice')
    def section_practice(id:str,section_id:str):
        from .writing_rounds import intentional_practice
        return intentional_practice(lab.workspace,id,section_id)

    @app.post('/api/workspace/papers/{id}/sections/{section_id}/writing/practice')
    def section_checkpoint(id:str,section_id:str,body:dict):
        from .writing_rounds import checkpoint
        return checkpoint(lab.workspace,id,section_id,body)

    @app.get('/api/workspace/papers/{id}/sections/{section_id}/writing/reviews')
    def section_reviews(id:str,section_id:str):return section_writing.reviews(id,section_id)

    @app.get('/api/workspace/papers/{id}/sections/{section_id}/writing/reviews/{review_id}')
    def section_review_status(id:str,section_id:str,review_id:str):return section_writing.review_status(id,section_id,review_id)

    @app.get('/api/workspace/papers/{id}/sections/{section_id}/writing/polishing-prompt')
    def section_polishing_prompt(id:str,section_id:str):return section_writing.polishing_prompt(id,section_id)

    @app.get('/api/workspace/papers/{id}/section-writing/resources')
    def section_resources(id:str,q:str='',tag:str='',kind:str='',version:str=''):return section_writing.resources(id,q,tag,kind,version)

    @app.post('/api/workspace/papers/{id}/section-writing/resources/{resource_id}/tags')
    def section_resource_tags(id:str,resource_id:str,body:dict):return section_writing.tag_resource(id,resource_id,body)

    @app.get('/api/workspace/papers/{id}/section-writing/figures/{figure_id}')
    def section_figure(id:str,figure_id:str):
        return FileResponse(section_writing.figure(id,figure_id))

    @app.get('/api/workspace/papers/{id}/outline-versions')
    def workspace_outline_versions(id:str):
        from .outline_import import history
        return history(lab.workspace,id)

    @app.get('/api/workspace/papers/{id}/outline-versions/{version_id}')
    def workspace_outline_version(id:str,version_id:str):
        from .outline_import import history
        return history(lab.workspace,id,version_id)

    @app.post('/api/workspace/papers/{id}/cards')
    def workspace_card_create(id:str,body:dict):
        if set(body)-{'title','kind','parent_id'} or not isinstance(body.get('title'),str) or len(body['title'])>150:raise ValueError('Supply a short card title.')
        return lab.workspace.add_card(id,body['title'],body.get('kind','argument'),body.get('parent_id'))

    @app.get('/api/workspace/papers/{id}/cards/{card_id}')
    def workspace_card(id:str,card_id:str):return lab.workspace.card(id,card_id)

    @app.post('/api/workspace/papers/{id}/cards/{card_id}/practice')
    def workspace_practice(id:str,card_id:str):
        from .paper_practice import prepare
        return prepare(lab,id,card_id)

    @app.post('/api/workspace/papers/{id}/cards/{card_id}/apply-attempt')
    def workspace_apply_attempt(id:str,card_id:str,body:dict):
        from .paper_practice import apply_attempt
        if not isinstance(body.get('attempt_id'),str):raise ValueError('Choose a saved writing attempt.')
        return apply_attempt(lab,id,card_id,body['attempt_id'],complete=body.get('complete') is True,expected_hash=body.get('base_hash'))

    @app.post('/api/workspace/papers/{id}/cards/{card_id}/complete')
    def workspace_complete(id:str,card_id:str,body:dict):
        from .paper_practice import complete_card
        if not isinstance(body.get('base_hash'),str):raise ValueError('Include the manuscript version you reviewed.')
        return complete_card(lab,id,card_id,body['base_hash'])

    @app.get('/api/workspace/papers/{id}/cards/{card_id}/review-drafts')
    def workspace_review_drafts(id:str,card_id:str):
        from .paper_practice import saved_reviews
        return saved_reviews(lab,id,card_id)

    @app.patch('/api/workspace/papers/{id}/notes/{note_id}')
    def workspace_save(id:str,note_id:str,body:dict):
        if set(body)-{'base_hash','fields','merge_heads','title'} or not isinstance(body.get('base_hash'),str):raise ValueError('Include the version you started editing.')
        return lab.workspace.save(id,note_id,body['base_hash'],body.get('fields'),body.get('merge_heads'),title=body.get('title'))

    @app.get('/api/workspace/papers/{id}/notes/{note_id}/history')
    def workspace_history(id:str,note_id:str):return lab.workspace.history(id,note_id)

    @app.get('/api/workspace/papers/{id}/export')
    def workspace_export(id:str):
        from urllib.parse import quote
        from scripts.create_paper_workspace import portable_name
        title=lab.workspace.get(id)['title']
        return Response(lab.workspace.export(id),media_type='text/markdown',headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(portable_name(title)+'.md')})

    @app.post('/api/workspace/papers/{id}/latex-preview')
    def workspace_latex_preview(id:str,body:dict):
        from .workspace_latex import latex_preview
        return latex_preview(lab.workspace,id,body)

    @app.get('/api/workspace/papers/{id}/bibliography')
    def workspace_bibliography(id:str):
        from .workspace_latex import bibliography_catalogue
        return bibliography_catalogue(lab.workspace,id)

    @app.post('/api/workspace/papers/{id}/bibliography')
    def workspace_bibliography_save(id:str,body:dict):
        from .workspace_latex import save_bibliography
        return save_bibliography(lab.workspace,id,body)

    @app.post('/api/workspace/papers/{id}/bibliography/merge')
    def workspace_bibliography_merge(id:str,body:dict):
        from .workspace_latex import merge_bibliography
        return merge_bibliography(lab.workspace,id,body)

    @app.get('/api/workspace/literature')
    def workspace_literature(q:str='',topic:str='',status:str='',scope:str='notes',offset:int=0):
        return literature.search(q[:500],topic,status,scope,offset)

    @app.get('/api/workspace/literature/{id}')
    def workspace_literature_source(id:str):return literature.detail(id)

    @app.get('/api/workspace/papers/{id}/sources')
    def workspace_sources(id:str):return paper_sources.catalogue(id)

    @app.post('/api/workspace/papers/{id}/sources')
    def workspace_source_upload(id:str,body:dict):
        if not isinstance(body.get('filename'),str) or not isinstance(body.get('base64'),str):raise ValueError('Choose a manuscript file.')
        try:raw=base64.b64decode(body['base64'],validate=True)
        except ValueError:raise ValueError('The uploaded file could not be decoded.')
        return paper_sources.upload(id,body['filename'],raw,columns=body.get('columns',2),black_means_agreed=body.get('black_means_agreed') is True)

    @app.get('/api/workspace/papers/{id}/passages')
    def workspace_passages(id:str,q:str='',ink:str='all',source_id:str|None=None):return paper_sources.search(id,q,ink,source_id)

    @app.post('/api/workspace/papers/{id}/mapping')
    def workspace_mapping(id:str,body:dict):
        if any(not isinstance(body.get(k),str) for k in ('source_id','segment_id','decision','reason')):raise ValueError('Choose a passage and describe its role.')
        return {'text':paper_sources.mapping(id,**{k:body[k] for k in ('source_id','segment_id','decision','reason')})}

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity_error(request,error):return JSONResponse({'detail':'Conflicting or invalid records. Your existing work has been kept.'},status_code=409)

    @app.get('/api/health')
    def health():
        import hashlib
        return {'status':'ok','mode':'local','version':'0.25.1','application':'academic-writing-lab','display_name':'Writing Lab','instance_id':hashlib.sha256(str(store.path.resolve()).encode()).hexdigest()[:16]}

    def sessions_summary():
        rows=store.rows('SELECT s.id,s.exercise_id,s.updated,s.version,e.payload,(SELECT count(*) FROM attempts a WHERE a.session_id=s.id) AS attempts FROM sessions s JOIN exercises e ON e.id=s.exercise_id ORDER BY s.updated DESC')
        for r in rows:
            e=json.loads(r.pop('payload'));r.update(title=e['title'],skill_ids=e.get('skill_ids',[]))
        return rows

    @app.get('/api/bootstrap')
    def bootstrap():
        latest={}
        for r in store.rows('SELECT * FROM packs'):
            p=json.loads(r['payload'])
            if p['pack_id'] not in latest or p['version']>latest[p['pack_id']][1]['version']:latest[p['pack_id']]=(r,p)
        packs=[{'key':r['id'],**{k:v for k,v in p.items() if k in ('title','version','origin','sources')}} for r,p in latest.values()]
        current={p['key'] for p in packs}
        used={r['exercise_id'] for r in store.rows('SELECT DISTINCT exercise_id FROM sessions')}
        exercises=[]
        for r in store.rows('SELECT * FROM exercises'):
            if r['pack_id'] in current or r['id'] in used:
                e=lab.exercise(r);e['archived_version']=r['pack_id'] not in current;exercises.append(e)
        return {'test_workspace':os.getenv('AWL_TEST_WORKSPACE')=='1','token':token,'packs':packs,'exercises':exercises,
                'sessions':sessions_summary(),'profile':store.setting('profile',DEFAULT_PROFILE),'skills':SKILLS,
                'references':lab.materials['references'],'vault':str(lab.vault),
                'workspace':{'enabled':lab.workspace.status()['enabled'],'legacy_paper_id':lab.workspace.config().get('legacy_paper_id')},
                'learning':lab.curriculum.snapshot()}

    @app.get('/api/providers')
    async def runtimes():return await asyncio.gather(*(providers.model_inventory(p) for p in providers.URLS))

    @app.put('/api/settings')
    async def settings(body:Profile):
        inventory=await providers.model_inventory(body.provider)
        if body.model not in [m['id'] for m in inventory['models']]:raise ValueError('Choose an available local text model.')
        if body.verifier_model and body.verifier_model not in [m['id'] for m in inventory['models']]:raise ValueError('Choose an installed local model for the second reading.')
        if body.structure_model and body.structure_model not in [m['id'] for m in inventory['models']]:raise ValueError('Choose an installed local model for the Structure tutor.')
        store.set_setting('profile',body.model_dump());return body.model_dump()

    @app.post('/api/sessions')
    def session(body:SessionBody):return lab.session(body.exercise_key,body.fresh)

    @app.get('/api/sessions/{id}')
    def get_session(id:str):
        session=lab.get_session(id)
        session['jobs']=[lab.job(r['id']) for r in store.rows('SELECT j.id FROM jobs j JOIN attempts a ON a.id=j.attempt_id WHERE a.session_id=? ORDER BY j.created DESC',(id,))]
        return session

    @app.patch('/api/sessions/{id}')
    def draft(id:str,body:DraftBody):
        with store.connect() as db:
            r=db.execute('UPDATE sessions SET text=?,outline=?,version=version+1,updated=? WHERE id=? AND version=?',(body.text,body.outline,now(),id,body.base_version))
            if r.rowcount!=1:raise HTTPException(409,'This draft changed in another tab. Your browser copy is kept; reload the saved session to compare.')
        return {'saved':True,'version':body.base_version+1}

    @app.post('/api/submit')
    async def submit(body:Submit):
        args=body.model_dump();feedback=args.pop('request_feedback')
        attempt=lab.save_attempt(**args)
        session=lab.get_session(attempt['session_id'])
        result={'saved':True,'attempt_id':attempt['id'],'session_id':session['id'],'version':session['version'],
                'attempt_count':len(session['attempts']),'examples_unlocked':len(session['attempts'])>=2,**lab.check(attempt)}
        exercise=json.loads(store.one('SELECT payload FROM exercises WHERE id=?',(session['exercise_id'],))['payload'])
        if exercise.get('workspace_paper_id'):
            from .paper_practice import apply_attempt
            try:result['paper_save']=apply_attempt(lab,exercise['workspace_paper_id'],exercise['workspace_card_id'],attempt['id'])
            except (Conflict,ValueError) as error:result['paper_save_error']=str(error)
        if feedback:
            try:result['job']=await lab.queue_review(attempt['id'],'review_revision' if attempt['parent_id'] else 'initial_hint','review-'+body.request_key)
            except ValueError as e:result['feedback_error']=str(e)
        return result

    @app.post('/api/assistance')
    def assistance(body:Assistance):return lab.assistance(body.session_id,body.kind)

    @app.get('/api/teaching/exercises/{key}')
    def teaching_example(key:str):return lab.teaching.example(key)

    @app.post('/api/teaching/view')
    def teaching_view(body:TeachingView):return lab.teaching.view_example(body.session_id)

    @app.get('/api/teaching/toolbox')
    def toolbox(node_id:str|None=None):return lab.teaching.toolbox(node_id)

    @app.get('/api/reader-reviews')
    def reader_reviews():return lab.teaching.review_index()

    @app.get('/api/reader-reviews/{card_id}')
    def reader_review(card_id:str):return lab.teaching.review(card_id)

    @app.get('/api/wording-flags')
    def wording_flags():return store.setting('wording_flags',[])

    @app.post('/api/wording-flags')
    def wording_flag(body:WordingFlag):return lab.teaching.report(**body.model_dump())

    @app.patch('/api/wording-flags/{id}')
    def wording_flag_status(id:str,body:FlagStatus):return lab.teaching.resolve_report(id,body.status)

    @app.get('/api/wording-flags-export')
    def wording_flags_export():
        return Response(json.dumps(store.setting('wording_flags',[]),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="writing-lab-comments.json"'})

    @app.post('/api/reviews')
    async def review(body:ReviewBody):return await lab.queue_review(body.attempt_id,body.kind,body.request_key)

    @app.get('/api/jobs/{id}')
    def job(id:str):return lab.job(id)

    @app.get('/api/activity')
    def activity():return lab.activity()

    @app.post('/api/jobs/{id}/cancel')
    def cancel(id:str):return lab.cancel(id)

    @app.post('/api/jobs/{id}/challenge')
    def challenge(id:str,body:dict):
        job=lab.job(id)
        if job['status']!='complete':raise ValueError('Wait until the review is complete.')
        message=body.get('message','')
        if not isinstance(message,str) or not 1<=len(message)<=2500:raise ValueError('Explain what seems incorrect.')
        attempt=store.one('SELECT session_id FROM attempts WHERE id=?',(job['attempt_id'],))
        lab.store.event(attempt['session_id'],'feedback_disputed',{'job_id':id,'message':message})
        return {'saved':True,'message':'Your disagreement is recorded. Tutor suggestions are not final grades.'}

    @app.get('/api/sources')
    def sources(q:str=''):
        rows=store.rows('SELECT * FROM sources ORDER BY rowid DESC');seen=set();result=[]
        for r in rows:
            if r['source_key'] in seen:continue
            seen.add(r['source_key']);p=json.loads(r['payload'])
            if q.casefold() not in (p['title']+' '+p['brief']).casefold():continue
            result.append({'id':r['id'],**{k:v for k,v in p.items() if k not in ('raw','brief','metadata')}})
        return result[:200]

    @app.get('/api/sources/{id}')
    def source(id:str):
        r=store.one('SELECT * FROM sources WHERE id=?',(id,))
        if not r:raise ValueError('Source not found.')
        p=json.loads(r['payload'])
        return {'id':r['id'],**p,'obsidian':companion.source_status(p)}

    @app.post('/api/sources/{id}/refresh')
    def refresh_source(id:str):
        r=store.one('SELECT * FROM sources WHERE id=?',(id,))
        if not r:raise ValueError('Source not found.')
        p=json.loads(r['payload'])
        new_id=import_source(store,safe_source(p['path'],lab.vault),lab.vault)
        return {'id':new_id,'changed':new_id!=id}

    @app.get('/api/obsidian')
    def companion_status():return companion.status()

    @app.get('/api/obsidian/guide')
    def companion_guide():
        path=ROOT/'docs/obsidian-ipad-guide.md'
        if not path.is_file():path=ROOT/'docs/portable-sync.md'
        if not path.is_file():raise HTTPException(404,detail='The device guide is not included in this installation.')
        return FileResponse(path,media_type='text/plain')

    @app.post('/api/obsidian/modules')
    def companion_export(body:CompanionModule):return companion.export_module(body.module_id)

    @app.post('/api/obsidian/snapshot')
    def companion_snapshot():return companion.snapshot()

    @app.get('/api/obsidian/preview')
    def companion_preview():return companion.preview()

    @app.post('/api/obsidian/import')
    def companion_import(body:CompanionImport):return companion.import_answers([s.model_dump() for s in body.selected])

    @app.post('/api/sources/import')
    def source_import(body:dict):
        paths=body.get('paths',[])
        if not isinstance(paths,list) or not 1<=len(paths)<=20:raise ValueError('Choose 1–20 source paths.')
        safe=[safe_source(p,lab.vault) for p in paths]
        return {'ids':[import_source(store,p,lab.vault) for p in safe]}

    @app.post('/api/packs/build')
    def builder(body:Build):
        if not body.confirmed:raise ValueError('Confirm the ideas before creating exercises.')
        rows=[store.one('SELECT * FROM sources WHERE id=?',(id,)) for id in body.source_ids]
        if any(r is None for r in rows):raise ValueError('A selected source is missing.')
        pack,answers=build_pack(body.title,body.outline,rows,body.skill)
        if body.paragraph_only:
            pack['exercises']=pack['exercises'][-1:];answers['answers']=answers['answers'][-1:]
        return import_pack(store,pack,answers)

    @app.post('/api/packs/import')
    def pack_import(body:dict):return import_pack(store,body.get('pack',{}),body.get('answers',{}))

    @app.get('/api/packs/{key}/export')
    def pack_export(key:str):
        row=store.one('SELECT * FROM packs WHERE id=?',(key,))
        if not row:raise ValueError('Pack not found.')
        pack=json.loads(row['payload']);answers={'schema':'awl.answer-key.v1','pack_id':pack['pack_id'],'pack_version':pack['version'],
          'answers':[json.loads(r['answer']) for r in store.rows('SELECT answer FROM exercises WHERE pack_id=?',(key,))]}
        practice=['# '+pack['title'],'','Source ideas are learning material. Write your own answers.','']
        for e in pack['exercises']:
            practice += ['## '+e['title'],'',e['prompt'],'']
            practice += [p['id']+' — '+p['text'] for p in e.get('parts',[])]
            if e.get('choices'):practice+=['Word bank: '+' / '.join(e['choices'])]
            practice += ['','Your answer:','', 'Criteria:']+['- '+c for c in e.get('criteria',[])]+['']
        keytext=['# Answer key — consult after your own attempts','']
        for a in answers['answers']:keytext+=['## '+a['id'],'',a.get('example') or ' / '.join(a.get('expected_values',[])) or 'Open writing: use the task criteria.','',a.get('explanation',''),'']
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr(pack['pack_id']+'.exercises.json',json.dumps(pack,indent=2,ensure_ascii=False))
            z.writestr(pack['pack_id']+'.answers.json',json.dumps(answers,indent=2,ensure_ascii=False))
            z.writestr('Practice.md','\n'.join(practice));z.writestr('Answers.md','\n'.join(keytext))
        return Response(out.getvalue(),media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="{pack["pack_id"]}.zip"'})

    @app.get('/api/progress')
    def progress():
        return {'sessions':sessions_summary(),'attempts':store.one('SELECT count(*) n FROM attempts')['n'],
                'feedback':store.one("SELECT count(*) n FROM jobs WHERE status='complete'")['n'],
                'hints':store.one("SELECT count(*) n FROM events WHERE kind='hint_displayed'")['n'],
                'examples':store.one("SELECT count(*) n FROM events WHERE kind='example_answer_displayed'")['n'],
                'disputes':store.one("SELECT count(*) n FROM events WHERE kind='feedback_disputed'")['n']}

    @app.get('/api/courses')
    def courses():return lab.curriculum.snapshot()

    @app.post('/api/course-completion-review')
    def completion_review(body:CompletionReview):
        if len(body.reflection.strip())<10:raise ValueError('Write a short note about what you checked or changed (at least 10 characters).')
        row=store.one('SELECT e.payload FROM attempts a JOIN sessions s ON s.id=a.session_id JOIN exercises e ON e.id=s.exercise_id WHERE a.id=?',(body.attempt_id,))
        exercise=json.loads(row['payload']) if row else {}
        if exercise.get('workspace_paper_id'):
            from .paper_practice import apply_attempt
            apply_attempt(lab,exercise['workspace_paper_id'],exercise['workspace_card_id'],body.attempt_id,complete=True)
        return lab.curriculum.acknowledge(body.attempt_id,body.reflection)

    @app.get('/api/certificates/{kind}/{id}')
    def certificate(kind:str,id:str):
        return Response(lab.curriculum.certificate(kind,id),media_type='text/html',
                        headers={'Content-Disposition':'attachment; filename="writing-lab-completion.html"'})

    @app.get('/api/paper')
    def paper():return lab.paper.summary()

    @app.get('/api/jobs/{id}/practice')
    def feedback_practice(id:str,node_id:str):
        from .wise_support import review_lessons
        return review_lessons(lab,id,node_id)

    @app.post('/api/writing-questions')
    async def writing_question(body:WritingQuestion):return await lab.text_coach.queue(**body.model_dump())

    @app.get('/api/writing-questions/history')
    def writing_question_history(exercise_key:str='',paper_id:str='',card_id:str=''):
        from .coaching_archive import question_history
        return {'questions':question_history(store,exercise_key=exercise_key,paper_id=paper_id,card_id=card_id)}

    @app.get('/api/writing-questions/{id}')
    def writing_question_status(id:str):return lab.text_coach.job(id)

    @app.post('/api/paper/word-help')
    async def word_help(body:WordRequest):return await lab.word_help.queue(**body.model_dump())

    @app.get('/api/paper/word-help/{id}')
    def word_help_status(id:str):return lab.word_help.job(id)

    @app.get('/api/revision')
    def revision():return lab.revision.overview()

    @app.get('/api/revision/argument/{node_id}')
    def revision_argument(node_id:str):
        from .passage_finder import argument_context
        return argument_context(lab,node_id)

    @app.get('/api/revision/search/{document_id}')
    def revision_search(document_id:str,node_id:str,q:str='',colour:str='all',include_structure:bool=False):
        return lab.passage_finder.search(document_id,node_id,q,colour,include_structure)

    @app.get('/api/revision/context/{document_id}/{segment_id}')
    def revision_context(document_id:str,segment_id:str):return lab.passage_finder.context_blocks(document_id,segment_id)

    @app.post('/api/revision/passage-readings')
    async def revision_passage_reading(body:PassageSearch):return await lab.passage_finder.queue(**body.model_dump())

    @app.get('/api/revision/passage-readings/{id}')
    def revision_passage_reading_status(id:str):return lab.passage_finder.job(id)

    @app.post('/api/revision/uploads')
    async def revision_upload(file:UploadFile=File(...),kind:str=Form(...),black_means_agreed:bool=Form(False),columns:int=Form(2)):
        from .wise_revision import MAX_UPLOAD
        raw=await file.read(MAX_UPLOAD+1)
        return await run_in_threadpool(lab.revision.upload,raw,file.filename or 'upload',kind,black_means_agreed,columns)

    @app.get('/api/revision/uploads/{id}')
    def revision_document(id:str):
        doc=lab.revision.document(id)
        return {k:v for k,v in doc.items() if k!='original'}

    @app.get('/api/revision/uploads/{id}/original')
    def revision_original(id:str):
        from urllib.parse import quote
        doc=lab.revision.document(id);pdf=doc['filename'].lower().endswith('.pdf')
        return Response(base64.b64decode(doc['original']),media_type='application/pdf' if pdf else 'application/octet-stream',
                        headers={'Content-Disposition':('inline' if pdf else 'attachment')+"; filename*=UTF-8''"+quote(doc['filename'],safe='')})

    @app.post('/api/revision/decisions')
    def revision_decision(body:RevisionDecision):return lab.revision.decision(body.base_version,body.model_dump(exclude={'base_version'}))

    @app.put('/api/revision/decisions/{id}')
    def revision_update(id:str,body:RevisionDecision):return lab.revision.decision(body.base_version,body.model_dump(exclude={'base_version'}),id)

    @app.post('/api/revision/placements')
    def revision_placement(body:PassagePlacement):return lab.revision.place(body.base_version,body.model_dump(exclude={'base_version'}))

    @app.get('/api/revision/candidates/{document_id}/{segment_id}')
    def revision_candidates(document_id:str,segment_id:str):return lab.revision.candidates(lab.revision.segment(document_id,segment_id)[1])

    @app.get('/api/revision/inspect/{document_id}/{segment_id}')
    def revision_inspect(document_id:str,segment_id:str):return lab.revision.inspect(document_id,segment_id)

    @app.post('/api/revision/reuse/{node_id}')
    def revision_reuse(node_id:str,body:PassageReuse):return lab.revision.reuse(node_id,body.base_version,**body.model_dump(exclude={'base_version'}))

    @app.get('/api/revision/export')
    def revision_export():return Response(lab.revision.export(),media_type='text/markdown',headers={'Content-Disposition':'attachment; filename="WISE-revision-decisions.md"'})

    @app.post('/api/revision/export/vault')
    def revision_vault():
        directory='06_Academic_Writing_Lab/Companion/WISE-Revisions/'+now()[:10]+'-'+uid()[:8]
        relative=directory+'/Revision decisions.md'
        companion.write_new(relative,lab.revision.export())
        companion.write_new(directory+'/Selected manuscript.md',lab.paper.export())
        from .backup_parts import split_backup
        parts=split_backup(store.snapshot())
        for filename,text in parts:companion.write_new(directory+'/Backup parts/'+filename,text)
        companion.write_new(directory+'/Workflow guide.md',(ROOT/'docs/wise-revision-workflow.md').read_text())
        companion.write_new(directory+'/wise-card-language-audit.md',(ROOT/'docs/wise-card-language-audit.md').read_text())
        for document in lab.revision.index():
            doc=lab.revision.document(document['id'])
            text=['# '+doc['filename'],'',doc['notice'],'']
            for seg in doc['segments']:text+=['## '+seg['locator'],f'Source block: {seg["id"]} · {seg["approval"]}',seg['text'],'']
            companion.write_new(directory+'/Sources/'+doc['id']+'.md','\n'.join(text))
        companion.write_new(directory+'/00 Start here.md','# WISE revision workspace\n\n[[Revision decisions]] · [[Selected manuscript]] · [[Workflow guide]]\n\nThe Sources folder contains extracted reading copies. The numbered Markdown files in Backup parts include the original uploaded bytes, saved exercises, feedback and revision records. Each is smaller than 5 MB. To restore on the Mac, open Settings and select ALL numbered Backup part files from this folder together. Checksums detect missing, mixed or damaged parts. Browser drafts and a running timer stay in that browser until saved.\n\nThese are dated snapshots. Obsidian edits do not silently replace the Mac manuscript. Upload new remarks or text as a new source, then review the proposed change. Let Obsidian Sync finish before switching devices.\n')
        return {'path':directory+'/00 Start here.md','uri':companion.uri(directory+'/00 Start here.md')}

    @app.get('/api/revision/support/{node_id}')
    def revision_support(node_id:str):
        from .wise_support import node_support
        return node_support(lab,node_id)

    @app.get('/api/revision/card-support/{card_id}')
    def revision_card_support(card_id:str):
        from .wise_support import card_support
        return card_support(lab,card_id)

    @app.post('/api/focus/sessions')
    def focus_session(body:FocusSession):return lab.revision.focus_log(body.model_dump())

    @app.put('/api/paper/plans/{id}')
    def argument_plan(id:str,body:ArgumentPlan):
        return lab.paper.workbench.plan(id,body.base_version,body.model_dump(exclude={'base_version'},exclude_none=True))

    @app.put('/api/paper/plan-order/{section}')
    def argument_order(section:str,body:ArgumentOrder):return lab.paper.workbench.order(section,body.base_version,body.node_ids)

    @app.post('/api/paper/apply-order/{section}')
    def manuscript_order(section:str,body:ApplyOrder):return lab.paper.workbench.apply_order(section,body.base_version)

    @app.put('/api/paper/reverse-outline/{attempt_id}')
    def reverse_outline(attempt_id:str,body:ReverseOutline):return lab.paper.workbench.reverse_outline(attempt_id,body.base_version,body.synopsis)

    @app.post('/api/paper/evidence')
    def add_evidence(body:EvidenceRecord):return lab.paper.workbench.evidence(body.base_version,body.model_dump(exclude={'base_version'}))

    @app.put('/api/paper/evidence/{id}')
    def update_evidence(id:str,body:EvidenceRecord):return lab.paper.workbench.evidence(body.base_version,body.model_dump(exclude={'base_version'}),id)

    @app.get('/api/paper/plan-export')
    def plan_export():return Response(lab.paper.workbench.export(),media_type='text/markdown',headers={'Content-Disposition':'attachment; filename="WISE-argument-plan.md"'})

    @app.get('/api/guides/{id}')
    def guide_download(id:str):
        files={'portable':'portable-user-guide.md','draft-to-paper':'draft-to-paper-guide.md','argument-finder':'argument-map-and-passage-finder.md','wise-walkthrough':'wise-walkthrough-review.md','focus':'focused-writing-guide.md','wise-card-language':'wise-card-language-audit.md','wise-revision':'wise-revision-workflow.md','user-guide':'user-guide.md','learning-plan':'wise-learning-plan.md','advanced-english':'advanced-english-analysis.md',
               'reader-review':'wise-critical-reader-review.md','card-reviews':'wise-card-reviews.md','feedback-architecture':'feedback-architecture.md','feedback-validation':'feedback-validation.md'}
        if id not in files:raise HTTPException(404,detail='Guide not found.')
        path=ROOT/'docs'/files[id]
        if not path.is_file():raise HTTPException(404,detail='This guide is not included in this installation. Open Help for the current setup guide.')
        return FileResponse(path,media_type='text/markdown',filename=files[id])

    @app.get('/api/paper/readings/{id}')
    def paper_reading(id:str):
        from .readings import ReadingUnavailable, resolve_reading
        paths={b['id']:b.get('path','') for b in lab.paper.blueprint.get('books',[])}
        paths.update({b['id']:b.get('path','') for b in lab.teaching.advanced.get('books',[])})
        if lab.paper.blueprint.get('overview_path'):paths['OVERVIEW']=lab.paper.blueprint['overview_path']
        try:path=resolve_reading(id,paths,lab.vault)
        except ReadingUnavailable as error:raise HTTPException(404,detail=str(error)) from error
        return FileResponse(path,media_type='application/pdf')

    @app.get('/api/teaching/phrasebook')
    def phrasebook(node_id:str|None=None):
        return lab.teaching.phrasebook(node_id)

    @app.get('/api/paper/cards')
    def paper_cards(q:str='',in_paper:bool=False):
        return [{k:v for k,v in c.items() if k not in ('raw','latex')} for c in lab.paper.cards.values()
                if (not in_paper or c['in_paper']) and q.casefold() in (c['id']+' '+c['title']+' '+c['latex']).casefold()]

    @app.get('/api/paper/cards/{id}')
    def paper_card(id:str):
        if id not in lab.paper.cards:raise ValueError('Source card not found.')
        return lab.paper.cards[id]

    @app.put('/api/paper/nodes/{id}')
    def paper_select(id:str,body:PaperSelection):
        return lab.paper.save(id,body.base_version,attempt_id=body.attempt_id,source_ids=body.source_ids,confirmed=body.confirmed,clear_selection=body.clear_selection)

    @app.get('/api/paper/export')
    def paper_export():
        return Response(lab.paper.export(),media_type='text/markdown',headers={'Content-Disposition':'attachment; filename="WISE-my-working-manuscript.md"'})

    @app.post('/api/paper/export/vault')
    def paper_export_vault():
        folder=lab.vault/'06_Academic_Writing_Lab/Learning_Exports'
        if not folder.resolve().is_relative_to(lab.vault.resolve()):raise ValueError('Export directory must be within the vault.')
        folder.mkdir(parents=True,exist_ok=True)
        path=folder/(f'WISE-My-Manuscript-{now()[:10]}-{uid()[:8]}.md')
        with path.open('x',encoding='utf-8') as f:f.write(lab.paper.export())
        return {'path':str(path),'saved':True}

    @app.get('/api/exports/{id}')
    def export(id:str):return Response(lab.export_session(id),media_type='text/markdown',headers={'Content-Disposition':f'attachment; filename="writing-{id}.md"'})

    @app.post('/api/exports/{id}/vault')
    def export_vault(id:str):
        text=lab.export_session(id)
        folder=lab.vault/'06_Academic_Writing_Lab/Learning_Exports'
        if not folder.resolve().is_relative_to(lab.vault.resolve()):raise ValueError('Export directory must be within the vault.')
        folder.mkdir(parents=True,exist_ok=True)
        path=folder/(f'Practice-{now()[:10]}-{uid()[:8]}.md')
        with path.open('x',encoding='utf-8') as f:f.write(text)
        return {'path':str(path),'saved':True}

    @app.get('/api/backup')
    def backup():return JSONResponse(store.snapshot(),headers={'Content-Disposition':'attachment; filename="Academic-Writing-Lab-backup.json"'})

    @app.post('/api/restore/preview')
    def preview_restore(body:dict):
        from .backup_parts import unpack_backup
        body=unpack_backup(body)
        validate_backup(body);return {'counts':{k:len(v) for k,v in body['tables'].items()},'created':body.get('created')}

    @app.post('/api/restore')
    async def restore(body:dict):
        from .backup_parts import unpack_backup
        body=unpack_backup(body);validate_backup(body)
        await lab.close();return await run_in_threadpool(store.restore,body)

    @app.post('/api/imports/legacy')
    def legacy(body:dict):return lab.import_legacy(body)

    app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='ui')
    return app

app=create_app()
