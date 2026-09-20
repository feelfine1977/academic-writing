import asyncio
import io
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import wave

from fastapi import UploadFile
import pytest

from backend.storage import Store
from backend.voice_notes import VoiceNotes, EditVoice, TranscribeVoice, MAX_UPLOAD
from backend.workspace import Workspace, Conflict, atomic_write, frontmatter, split_note


def make(tmp_path, monkeypatch):
    vault=tmp_path/'Vault';(vault/'.obsidian').mkdir(parents=True)
    lab=SimpleNamespace(vault=vault,store=Store(tmp_path/'data'),semaphore=asyncio.Semaphore(1))
    lab.workspace=Workspace(lab);lab.workspace.configure(str(vault))
    paper=lab.workspace.create('A field study','## Section: Introduction\n### Argument: Context\n- Measurements describe recorded conditions.\n')
    voice=VoiceNotes(lab)
    runtime=tmp_path/'fake-runtime';runtime.write_text('test')
    monkeypatch.setattr(voice,'runtime',lambda:{'engine':runtime,'decoder':runtime,'model':runtime})
    def decode(source,destination):
        with wave.open(str(destination),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000);stream.writeframes(b'\0\0'*16000)
        return 1.0,False
    monkeypatch.setattr(voice,'decode',decode)
    return voice,paper['id'],paper['nodes'][0]['id']


async def upload(voice,pid,sid,key='capture-1',data=b'original audio'):
    return await voice.upload(pid,UploadFile(io.BytesIO(data),filename='my notes.wav'),sid,'context','Opening idea','en',key)


class FakeProcess:
    def __init__(self,text,command,blocked=None):
        self.returncode=None;self.blocked=blocked
        output=Path(command[command.index('-of')+1]).with_suffix('.json')
        output.write_text(json.dumps({'result':{'language':'en'},'transcription':[{'text':text,'offsets':{'from':0,'to':900}}]}))
    async def communicate(self):
        if self.blocked:await self.blocked.wait()
        self.returncode=0;return b'',b''
    def kill(self):self.returncode=-9
    async def wait(self):return self.returncode


def engine(monkeypatch,text='I observed a difference.',blocked=None):
    calls=[]
    async def create(*command,**kwargs):
        calls.append(command);return FakeProcess(text,command,blocked)
    monkeypatch.setattr(asyncio,'create_subprocess_exec',create)
    return calls


def test_audio_saved_portably_idempotent_and_never_changes_manuscript(tmp_path,monkeypatch):
    voice,pid,sid=make(tmp_path,monkeypatch)
    before=voice.workspace.card(pid,sid)['hash']
    async def run():
        first=await upload(voice,pid,sid)
        again=await upload(voice,pid,sid)
        assert first['id']==again['id'] and first['status']=='saved'
        assert first['corrected_text']==first['original_text']==''
        note=voice.locate(pid,first['id'])
        audio=voice.asset(note,note['meta']['audio_relative_path'],'Audio')
        assert audio.read_bytes()==b'original audio'
        assert 'Section writing/Voice notes/' in first['vault_path']
        assert 'Opening idea' in first['vault_path']
        assert len(voice.list(pid,sid)['notes'])==1
        with pytest.raises(Conflict):await upload(voice,pid,sid,data=b'different audio')
        assert voice.workspace.card(pid,sid)['hash']==before
    asyncio.run(run())


def test_transcription_retains_original_and_retry_preserves_corrected_notes(tmp_path,monkeypatch):
    voice,pid,sid=make(tmp_path,monkeypatch)
    calls=engine(monkeypatch)
    async def run():
        note=await upload(voice,pid,sid)
        queued=await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='first'))
        assert queued['status']=='queued'
        await asyncio.gather(*list(voice.tasks.values()))
        result=voice.get(pid,note['id'])
        assert result['status']=='complete' and result['original_text']=='I observed a difference.'
        assert result['corrected_text']==result['original_text']
        assert result['segments']==[{'start':0.0,'end':0.9,'text':'I observed a difference.'}]
        assert len(calls)==1
        await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='first'))
        assert len(calls)==1
        edited=voice.edit(pid,note['id'],EditVoice(base_hash=result['hash'],corrected_text='My corrected description.',ideas_text='Check the measurement.'))
        engine(monkeypatch,'A second machine reading.')
        await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='retry'))
        await asyncio.gather(*list(voice.tasks.values()))
        retried=voice.get(pid,note['id'])
        assert retried['original_text']=='I observed a difference.'
        assert retried['corrected_text']=='My corrected description.'
        assert retried['ideas_text']=='Check the measurement.'
        assert len(retried['transcripts'])==2
        assert retried['latest_text']=='A second machine reading.'
        version=voice.transcript(voice.locate(pid,note['id']),retried['transcripts'][-1]['id'])
        assert version['text']=='A second machine reading.'
        assert list(voice.folder(pid).glob('Recovered files/**/*.md'))
        with pytest.raises(Conflict):voice.edit(pid,note['id'],EditVoice(base_hash=edited['hash'],corrected_text='Old editor'))
        assert voice.get(pid,note['id'])['corrected_text']=='My corrected description.'
    asyncio.run(run())


def test_corrections_made_during_recognition_survive_result(tmp_path,monkeypatch):
    voice,pid,sid=make(tmp_path,monkeypatch)
    async def run():
        gate=asyncio.Event();calls=engine(monkeypatch,blocked=gate)
        note=await upload(voice,pid,sid)
        await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='first'))
        while not calls:await asyncio.sleep(.001)
        current=voice.get(pid,note['id'])
        voice.edit(pid,note['id'],EditVoice(base_hash=current['hash'],corrected_text='My own notes while I waited.'))
        gate.set();await asyncio.gather(*list(voice.tasks.values()))
        complete=voice.get(pid,note['id'])
        assert complete['original_text']=='I observed a difference.'
        assert complete['corrected_text']=='My own notes while I waited.'
    asyncio.run(run())


def test_cancel_before_worker_started_and_while_worker_running(tmp_path,monkeypatch):
    voice,pid,sid=make(tmp_path,monkeypatch)
    async def run():
        gate=asyncio.Event();calls=engine(monkeypatch,blocked=gate)
        note=await upload(voice,pid,sid)
        await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='queued'))
        cancelled=await voice.cancel(pid,note['id'])
        assert cancelled['status']=='cancelled' and not calls
        await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='running'))
        while not calls:await asyncio.sleep(.001)
        cancelled=await voice.cancel(pid,note['id'])
        assert cancelled['status']=='cancelled' and not cancelled['transcripts']
        assert cancelled['original_text']==''
    asyncio.run(run())


def test_silence_never_calls_speech_model(tmp_path,monkeypatch):
    voice,pid,sid=make(tmp_path,monkeypatch)
    calls=engine(monkeypatch,'Hallucinated words.')
    monkeypatch.setattr(voice,'decode',lambda *_:(1.0,True))
    async def run():
        note=await upload(voice,pid,sid)
        await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='silence'))
        await asyncio.gather(*list(voice.tasks.values()))
        result=voice.get(pid,note['id'])
        assert result['status']=='complete' and result['original_text']=='' and not calls
        assert 'No speech detected' in result['error']
    asyncio.run(run())


def test_shared_inference_queue_and_restart_recovery(tmp_path,monkeypatch):
    voice,pid,sid=make(tmp_path,monkeypatch);calls=engine(monkeypatch)
    async def run():
        note=await upload(voice,pid,sid)
        await voice.lab.semaphore.acquire()
        await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='blocked'))
        await asyncio.sleep(.01)
        assert not calls and voice.get(pid,note['id'])['status']=='queued'
        # Recreate persisted state as a crashed process would leave it.
        job_path=next((voice.local/'jobs').glob('*.json'));job=json.loads(job_path.read_text())
        await voice.close()
        current=voice.locate(pid,note['id']);voice.revise(current,{'status':'transcribing','job_id':job['id']})
        job['status']='transcribing';voice.save_job(job)
        voice.recover()
        assert voice.get(pid,note['id'])['status']=='failed'
        assert 'restarted' in voice.get(pid,note['id'])['error']
        voice.lab.semaphore.release()
    asyncio.run(run())


def test_paths_cannot_escape_or_follow_audio_symlink(tmp_path,monkeypatch):
    voice,pid,sid=make(tmp_path,monkeypatch)
    async def run():
        result=await upload(voice,pid,sid);note=voice.locate(pid,result['id'])
        with pytest.raises(ValueError):voice.asset(note,'Audio/../../private.txt','Audio')
        with pytest.raises(ValueError):voice.asset(note,'/tmp/private.wav','Audio')
        with pytest.raises(ValueError):voice.locate(pid,'../anything')
        target=tmp_path/'outside.wav';target.write_bytes(b'outside')
        link=Path(note['path']).parent/'Audio'/'link.wav';link.symlink_to(target)
        with pytest.raises(ValueError):voice.asset(note,'Audio/link.wav','Audio')
    asyncio.run(run())


def test_real_decoder_rejects_non_audio_and_accepts_silent_wav(tmp_path,monkeypatch):
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:pytest.skip('FFmpeg not installed in this test environment')
    voice,pid,sid=make(tmp_path,monkeypatch)
    monkeypatch.setattr(voice,'runtime',lambda:{'decoder':Path(ffmpeg),'engine':None,'model':None})
    source=tmp_path/'fake.wav';source.write_bytes(b'This is not audio.')
    with pytest.raises(ValueError):VoiceNotes.decode(voice,source,tmp_path/'output.wav')
    with wave.open(str(source),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000);stream.writeframes(b'\0\0'*16000)
    duration,silent=VoiceNotes.decode(voice,source,tmp_path/'output.wav')
    assert duration==1 and silent


def test_new_machine_reads_voice_note_without_old_local_paths(tmp_path,monkeypatch):
    voice,pid,sid=make(tmp_path/'Mac',monkeypatch)
    async def run():
        result=await upload(voice,pid,sid)
        target=tmp_path/'Windows'/'Vault';shutil.copytree(voice.lab.vault,target)
        lab=SimpleNamespace(vault=target,store=Store(tmp_path/'Windows'/'data'),semaphore=asyncio.Semaphore(1))
        lab.workspace=Workspace(lab);lab.workspace.configure(str(target))
        other=VoiceNotes(lab);read=other.get(pid,result['id'])
        assert read['original_text']=='' and read['id']==result['id']
        note=other.locate(pid,result['id']);assert other.asset(note,note['meta']['audio_relative_path'],'Audio').is_file()
        assert not other.status()['model_ready']
    asyncio.run(run())


def test_upload_bounds_and_missing_engine_keep_audio_saved(tmp_path,monkeypatch):
    voice,pid,sid=make(tmp_path,monkeypatch)
    async def run():
        with pytest.raises(ValueError):
            await voice.upload(pid,UploadFile(io.BytesIO(b'bad'),filename='playlist.m3u'),sid,'','','en','bad-file')
        with pytest.raises(ValueError):await upload(voice,pid,sid,data=b'')
        monkeypatch.setattr('backend.voice_notes.MAX_UPLOAD',10)
        with pytest.raises(ValueError):await upload(voice,pid,sid,data=b'x'*11)
        monkeypatch.setattr('backend.voice_notes.MAX_UPLOAD',MAX_UPLOAD)
        note=await upload(voice,pid,sid)
        monkeypatch.setattr(voice,'runtime',lambda:{'decoder':None,'engine':None,'model':None})
        with pytest.raises(ValueError):await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='unavailable'))
        assert voice.get(pid,note['id'])['status']=='saved'
        assert voice.locate(pid,note['id'])['meta']['audio_sha256']
    asyncio.run(run())


def test_voice_api_token_upload_and_audio_contract(tmp_path,monkeypatch):
    from backend.main import create_app
    from fastapi.testclient import TestClient
    vault=tmp_path/'Vault';(vault/'.obsidian').mkdir(parents=True)
    app=create_app(data_dir=tmp_path/'data',vault_root=vault,auto_tutor=False)
    app.state.lab.workspace.configure(str(vault))
    paper=app.state.lab.workspace.create('New paper','## Section: Introduction\n### Argument: Context\n- An idea.\n')
    pid=paper['id'];sid=paper['nodes'][0]['id']
    voice=app.state.voice_notes;monkeypatch.setattr(voice,'decode',lambda *_:(1.0,False))
    base=f'/api/workspace/papers/{pid}/voice-notes'
    with TestClient(app,base_url='http://127.0.0.1:8765') as client:
        assert client.get('/api/voice/status').status_code==200
        payload={'section_id':sid,'idea_id':'context','language':'auto','request_key':'api-recording','transcribe':'false'}
        assert client.post(base,data=payload,files={'file':('audio.wav',b'recorded audio','audio/wav')}).status_code==403
        headers={'Origin':'http://127.0.0.1:8765'}
        result=client.post(base,headers=headers,data=payload,files={'file':('audio.wav',b'recorded audio','audio/wav')})
        assert result.status_code==200,result.text
        note=result.json();assert note['status']=='saved'
        assert client.get(base,params={'section_id':sid}).json()['notes'][0]['id']==note['id']
        audio=client.get(note['audio_url']);assert audio.content==b'recorded audio'
        assert audio.headers['content-type']=='audio/wav'
        assert "media-src 'self' blob:" in audio.headers['content-security-policy']
        updated=client.patch(base+'/'+note['id'],headers=headers,json={'base_hash':note['hash'],'corrected_text':'Author notes.','ideas_text':'One idea.'})
        assert updated.status_code==200 and updated.json()['corrected_text']=='Author notes.'
        stale=client.patch(base+'/'+note['id'],headers=headers,json={'base_hash':note['hash'],'corrected_text':'Old editor'})
        assert stale.status_code==409 and stale.json()['current']['corrected_text']=='Author notes.'


def test_apple_locale_and_note_headings_are_portable(tmp_path,monkeypatch):
    from backend.voice_notes import language
    assert language('en-GB')=='en' and language('de-DE')=='de' and language('pl-PL')=='pl'
    voice,pid,sid=make(tmp_path,monkeypatch)
    async def run():
        result=await upload(voice,pid,sid)
        with pytest.raises(ValueError):voice.edit(pid,result['id'],EditVoice(base_hash=result['hash'],corrected_text='My notes.\n\n## Unintended field\nText'))
        assert voice.get(pid,result['id'])['hash']==result['hash']
        changed=voice.edit(pid,result['id'],EditVoice(base_hash=result['hash'],corrected_text='My notes.\n\n### A heading\nText'))
        assert '### A heading' in changed['corrected_text']
    asyncio.run(run())


def test_native_inline_json_frontmatter_and_apple_transcript_reopen(tmp_path,monkeypatch):
    from backend.workspace import update_fields
    voice,pid,sid=make(tmp_path,monkeypatch);engine(monkeypatch,'A desktop retry.')
    async def run():
        result=await upload(voice,pid,sid)
        note=voice.locate(pid,result['id']);meta=note['meta'];run_id='74e230ac-d556-47c5-88cb-2b66d7da7ca7'
        transcript={'id':run_id,'created':meta['created'],'text':'My original spoken idea.','segments':[{'start':0.0,'end':0.9,'text':'My original spoken idea.'}],'engine':'apple-speech-on-device','model':'SFSpeechRecognizer:en-GB','language':'en-GB'}
        relative='Transcripts/'+note['id']+'-'+run_id+'.json'
        atomic_write(voice.asset(note,relative,'Transcripts'),json.dumps(transcript))
        meta.update(status='complete',speech_language='en-GB',engine='apple-speech-on-device',model='SFSpeechRecognizer:en-GB',original_initialized=True,corrected_initialized=True,transcripts=[{k:transcript[k] for k in ('id','created','engine','model','language')}|{'path':relative}])
        head='---\n'+'\n'.join(k+': '+json.dumps(v) for k,v in meta.items())+'\n---\n'
        atomic_write(Path(note['path']),head+update_fields(note['_body'],{'Original transcription':transcript['text'],'My corrected spoken notes':'My iPad correction.'}))
        reopened=voice.get(pid,note['id'])
        assert reopened['language']=='en-GB' and reopened['original_text']=='My original spoken idea.'
        assert reopened['segments']==transcript['segments']
        await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='mac-retry'))
        await asyncio.gather(*list(voice.tasks.values()))
        latest=voice.get(pid,note['id'])
        assert latest['original_text']=='My original spoken idea.' and latest['corrected_text']=='My iPad correction.'
        assert latest['latest_text']=='A desktop retry.' and len(latest['transcripts'])==2
    asyncio.run(run())


def test_manual_obsidian_corrections_before_first_transcription_are_preserved(tmp_path,monkeypatch):
    from backend.workspace import update_fields
    voice,pid,sid=make(tmp_path,monkeypatch);engine(monkeypatch)
    async def run():
        result=await upload(voice,pid,sid);note=voice.locate(pid,result['id'])
        atomic_write(Path(note['path']),frontmatter(note['meta'])+update_fields(note['_body'],{'My corrected spoken notes':'Manually written in Obsidian.'}))
        await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='transcribe'))
        await asyncio.gather(*list(voice.tasks.values()))
        assert voice.get(pid,note['id'])['corrected_text']=='Manually written in Obsidian.'
    asyncio.run(run())


def test_runtime_falls_back_after_configured_engine_or_decoder_upgrade(tmp_path,monkeypatch):
    voice,pid,sid=make(tmp_path,monkeypatch)
    engine_path=tmp_path/'current-whisper-cli';engine_path.write_text('current engine')
    decoder_path=tmp_path/'current-ffmpeg';decoder_path.write_text('current decoder')
    voice.local.mkdir(parents=True,exist_ok=True)
    (voice.local/'config.json').write_text(json.dumps({'whisper_cli':str(tmp_path/'removed-version/whisper-cli'),'ffmpeg':str(tmp_path/'removed-version/ffmpeg')}))
    monkeypatch.setenv('AWL_FFMPEG',str(tmp_path/'removed-env-version/ffmpeg'))
    monkeypatch.setenv('AWL_WHISPER_CLI',str(tmp_path/'removed-env-version/whisper-cli'))
    monkeypatch.setattr(shutil,'which',lambda name: str(decoder_path if name=='ffmpeg' else engine_path))
    runtime=VoiceNotes.runtime(voice)
    assert runtime['decoder']==decoder_path and runtime['engine']==engine_path


def test_runtime_keeps_valid_configured_paths_and_stable_symlinks(tmp_path,monkeypatch):
    voice,pid,sid=make(tmp_path,monkeypatch)
    old_target=tmp_path/'version1-ffmpeg';old_target.write_text('current')
    stable=tmp_path/'ffmpeg';stable.symlink_to(old_target)
    replacement=tmp_path/'other-ffmpeg';replacement.write_text('other')
    voice.local.mkdir(parents=True,exist_ok=True)
    (voice.local/'config.json').write_text(json.dumps({'ffmpeg':str(stable)}))
    monkeypatch.delenv('AWL_FFMPEG',raising=False)
    monkeypatch.setattr(shutil,'which',lambda name:str(replacement))
    assert VoiceNotes.runtime(voice)['decoder']==stable
    old_target.unlink();stable.unlink();stable.symlink_to(replacement)
    assert VoiceNotes.runtime(voice)['decoder']==stable


def test_trash_is_recoverable_hides_from_list_and_cancels_transcription(tmp_path,monkeypatch):
    voice,pid,sid=make(tmp_path,monkeypatch)
    async def run():
        note=await upload(voice,pid,sid)
        edited=voice.edit(pid,note['id'],EditVoice(base_hash=note['hash'],corrected_text='Keep my corrections.'))
        audio_note=voice.locate(pid,note['id']);audio=voice.asset(audio_note,audio_note['meta']['audio_relative_path'],'Audio')
        await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='queued'))
        deleted=await voice.trash(pid,note['id'])
        assert deleted['trashed'] and deleted['status']=='cancelled'
        assert deleted['corrected_text']=='Keep my corrections.' and audio.read_bytes()==b'original audio'
        assert not voice.list(pid,sid)['notes']
        assert voice.list(pid,sid,include_trashed=True)['notes'][0]['id']==note['id']
        with pytest.raises(ValueError,match='Restore'):await voice.transcribe(pid,note['id'],TranscribeVoice(request_key='deleted'))
        restored=voice.restore(pid,note['id'])
        assert not restored['trashed'] and restored['trashed_at']==''
        assert restored['corrected_text']=='Keep my corrections.' and len(voice.list(pid,sid)['notes'])==1
    asyncio.run(run())


def test_merge_order_idempotency_and_atomic_provenance_keep_originals(tmp_path,monkeypatch):
    from backend.voice_notes import MergeVoice
    import backend.voice_notes as module
    voice,pid,sid=make(tmp_path,monkeypatch);encodings=[]
    def encode(notes,directory):
        encodings.append([n['id'] for n in notes]);target=directory/'merged.m4a';target.write_bytes(b'merged audio');return target
    monkeypatch.setattr(voice,'encode_merge',encode)
    async def run():
        first=await upload(voice,pid,sid,'first',b'first audio');second=await upload(voice,pid,sid,'second',b'second audio')
        hashes={n['id']:n['hash'] for n in [first,second]}
        body=MergeVoice(note_ids=[second['id'],first['id']],title='My combined idea',language='en',request_key='merge-1')
        native_write=module.atomic_write;published=[]
        def inspect(path,raw,**kwargs):
            if path.suffix=='.md' and 'merged_from:' in raw:
                meta,contents=split_note(raw)
                assert meta['merge_signature'] and meta['merge_request_key']=='merge-1'
                assert '## Merged recordings' in contents
                published.append(meta)
            return native_write(path,raw,**kwargs)
        monkeypatch.setattr(module,'atomic_write',inspect)
        result=await voice.merge(pid,body)
        assert result['status']=='saved' and result['original_text']==result['corrected_text']==''
        assert [n['id'] for n in result['merged_from']]==body.note_ids and len(published)==1
        assert result['audio_bytes']==len(b'merged audio')
        assert all(voice.get(pid,note_id)['hash']==hash_value for note_id,hash_value in hashes.items())
        again=await voice.merge(pid,body)
        assert again['id']==result['id'] and len(encodings)==1
        # Older native edits may have changed the generic upload key. The
        # dedicated merge key still identifies the existing merged recording.
        existing=voice.locate(pid,result['id']);voice.revise(existing,{'request_key':result['id']})
        after_native_edit=await voice.merge(pid,body)
        assert after_native_edit['id']==result['id'] and len(encodings)==1
        with pytest.raises(Conflict):await voice.merge(pid,MergeVoice(note_ids=list(reversed(body.note_ids)),request_key='merge-1'))
        assert len(voice.list(pid,sid)['notes'])==3
    asyncio.run(run())


def test_merge_rejects_deleted_changed_duplicate_and_cross_section_sources(tmp_path,monkeypatch):
    from backend.voice_notes import MergeVoice
    voice,pid,sid=make(tmp_path,monkeypatch)
    async def run():
        first=await upload(voice,pid,sid,'a',b'A');second=await upload(voice,pid,sid,'b',b'B')
        with pytest.raises(ValueError,match='once'):await voice.merge(pid,MergeVoice(note_ids=[first['id'],first['id']],request_key='same'))
        await voice.trash(pid,second['id'])
        with pytest.raises(ValueError,match='Restore'):await voice.merge(pid,MergeVoice(note_ids=[first['id'],second['id']],request_key='trashed'))
        voice.restore(pid,second['id'])
        second_note=voice.locate(pid,second['id']);voice.asset(second_note,second_note['meta']['audio_relative_path'],'Audio').write_bytes(b'externally changed')
        with pytest.raises(Conflict,match='changed'):await voice.merge(pid,MergeVoice(note_ids=[first['id'],second['id']],request_key='changed'))
        voice.revise(second_note,{'section_id':'another-section'})
        with pytest.raises(ValueError,match='same paper'):await voice.merge(pid,MergeVoice(note_ids=[first['id'],second['id']],request_key='cross-section'))
    asyncio.run(run())


def test_merge_checks_sources_again_immediately_before_publish(tmp_path,monkeypatch):
    from backend.voice_notes import MergeVoice
    voice,pid,sid=make(tmp_path,monkeypatch)
    async def run():
        first=await upload(voice,pid,sid,'first',b'A');second=await upload(voice,pid,sid,'second',b'B')
        def encode(notes,directory):
            output=directory/'merged.m4a';output.write_bytes(b'MERGED');return output
        monkeypatch.setattr(voice,'encode_merge',encode)
        decode=voice.decode
        def changing_decode(source,destination):
            result=decode(source,destination)
            if source.name=='input.m4a':
                note=voice.locate(pid,first['id']);voice.revise(note,{'trashed':True,'trashed_at':'now'})
            return result
        monkeypatch.setattr(voice,'decode',changing_decode)
        with pytest.raises(ValueError,match='Restore'):
            await voice.merge(pid,MergeVoice(note_ids=[first['id'],second['id']],request_key='concurrent-trash'))
        assert len(voice.list(pid,sid,True)['notes'])==2
    asyncio.run(run())


def test_merge_pcm_order_and_duration_cap(tmp_path,monkeypatch):
    from array import array
    from backend.voice_notes import MergeVoice
    import backend.voice_notes as module
    voice,pid,sid=make(tmp_path,monkeypatch);durations=[1.0,1.0];seen=[]
    def decode(source,destination):
        index=0 if source.read_bytes()==b'A' else 1
        samples=array('h',[1000 if index==0 else -2000]*16000)
        with wave.open(str(destination),'wb') as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(samples.tobytes())
        return durations[index],False
    def encode_run(command,**kwargs):
        with wave.open(command[command.index('-i')+1],'rb') as audio:
            samples=array('h',audio.readframes(audio.getnframes()));seen.extend([samples[0],samples[16000],len(samples)])
        Path(command[-1]).write_bytes(b'encoded');return SimpleNamespace(returncode=0)
    async def run():
        first=await upload(voice,pid,sid,'a',b'A');second=await upload(voice,pid,sid,'b',b'B')
        notes=voice.merge_sources(pid,[second['id'],first['id']])
        monkeypatch.setattr(voice,'decode',decode);monkeypatch.setattr(module.subprocess,'run',encode_run)
        target=tmp_path/'merge';target.mkdir()
        result=voice.encode_merge(notes,target)
        assert result.read_bytes()==b'encoded' and seen==[-2000,1000,32000]
        durations[:]=[350,350]
        with pytest.raises(ValueError,match='at most 10 minutes'):voice.encode_merge(notes,target)
    asyncio.run(run())
