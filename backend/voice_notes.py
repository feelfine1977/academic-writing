"""Private, portable spoken notes. Speech recognition never edits manuscript prose."""
from __future__ import annotations

import asyncio
from array import array
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote
import uuid
import wave

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from .workspace import Conflict, atomic_write, fields_of, frontmatter, sha, split_note, update_fields
from scripts.create_paper_workspace import portable_name

MAX_UPLOAD = 40_000_000
MAX_SECONDS = 600
LANGUAGES = ('auto', 'en', 'de', 'pl')
EXTENSIONS = {'.webm', '.m4a', '.mp4', '.mp3', '.wav', '.ogg', '.oga', '.flac', '.aac', '.caf', '.aif', '.aiff'}
MEDIA = {'.webm':'audio/webm', '.m4a':'audio/mp4', '.mp4':'audio/mp4', '.wav':'audio/wav', '.mp3':'audio/mpeg', '.ogg':'audio/ogg', '.oga':'audio/ogg', '.flac':'audio/flac', '.aac':'audio/aac', '.caf':'audio/x-caf', '.aif':'audio/aiff', '.aiff':'audio/aiff'}
ORIGINAL = 'Original transcription'
CORRECTED = 'My corrected spoken notes'
IDEAS = 'Ideas I chose to develop'
SYNC = 'Saved in this local Obsidian vault. Let Obsidian Sync finish before switching devices; remote delivery is not verified here.'


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise ValueError('Invalid voice note identity.')
    return value


def language(value):
    # Apple stores locale identifiers; whisper.cpp accepts the base language code.
    value=value.split('-',1)[0].lower() if isinstance(value,str) else value
    if value not in LANGUAGES:
        raise ValueError('Choose automatic detection, English, German or Polish.')
    return value


def request_key(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 200 or any(ord(c) < 32 for c in value):
        raise ValueError('Supply a valid recording request key.')
    return value


class EditVoice(BaseModel):
    model_config = ConfigDict(extra='forbid')
    base_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    corrected_text: str = Field(max_length=100000)
    ideas_text: str = Field(default='', max_length=30000)


class TranscribeVoice(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_key: str = Field(min_length=1, max_length=200)
    language: str | None = None


class MergeVoice(BaseModel):
    model_config = ConfigDict(extra='forbid')
    note_ids: list[str] = Field(min_length=2,max_length=10)
    title: str = Field(default='Merged spoken idea',min_length=1,max_length=160)
    language: str = 'auto'
    request_key: str = Field(min_length=1,max_length=200)


class VoiceNotes:
    def __init__(self, lab):
        self.lab = lab
        self.workspace = lab.workspace
        self.local = lab.store.directory / 'speech'
        self.tasks = {}
        self.processes = {}
        self.merge_lock = asyncio.Lock()

    def runtime(self):
        try:
            config = json.loads((self.local / 'config.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            config = {}
        if not isinstance(config,dict):config={}
        def executable(env, key, name):
            # Homebrew/package upgrades can remove a versioned configured path.
            # Test every candidate instead of allowing that stale path to mask
            # a working installation. Keep stable symlinks rather than resolve them.
            candidates = [os.getenv(env), config.get(key), shutil.which(name)]
            if sys.platform == 'darwin':
                candidates.extend(['/opt/homebrew/bin/' + name, '/usr/local/bin/' + name])
            candidates.append(self.local / 'bin' / (name + ('.exe' if os.name == 'nt' else '')))
            for candidate in candidates:
                if not isinstance(candidate, (str, Path)) or not candidate:
                    continue
                path = Path(candidate).expanduser()
                if path.is_file():
                    return path
            return None
        model = Path(os.getenv('AWL_WHISPER_MODEL') or config.get('model') or self.local / 'models' / 'ggml-small.bin').expanduser()
        return {'engine':executable('AWL_WHISPER_CLI', 'whisper_cli', 'whisper-cli'),
                'decoder':executable('AWL_FFMPEG', 'ffmpeg', 'ffmpeg'),
                'model':model if model.is_file() else None}

    def status(self):
        runtime = self.runtime()
        ready = all(runtime.values())
        missing = [label for key,label in [('decoder','audio decoder (FFmpeg)'),('engine','speech engine (whisper.cpp)'),('model','speech model')] if not runtime[key]]
        return {'ready':ready, 'engine_ready':bool(runtime['engine']), 'model_ready':bool(runtime['model']),
                'decoder_ready':bool(runtime['decoder']), 'engine':'whisper.cpp',
                'model':runtime['model'].name if runtime['model'] else '',
                'message':'Transcription runs locally on this computer.' if ready else 'Local setup needed: ' + ', '.join(missing) + '.',
                'max_upload_bytes':MAX_UPLOAD, 'max_duration_seconds':MAX_SECONDS, 'languages':list(LANGUAGES)}

    def folder(self, paper_id):
        return self.workspace.safe(self.workspace.locate(identifier(paper_id)).parent / 'Section writing' / 'Voice notes')

    def read_path(self, path):
        note = self.workspace.read(path)
        if note['meta'].get('awl_kind') != 'voice_note':
            raise ValueError('This is not a spoken note.')
        return note

    def locate(self, paper_id, note_id):
        identifier(note_id)
        found = []
        for path in self.folder(paper_id).glob('*.md'):
            note = self.read_path(path)
            if note['id'] == note_id:
                if note['meta'].get('paper_id') != paper_id:
                    raise ValueError('The spoken note belongs to another paper.')
                found.append(note)
        if len(found) != 1:
            raise ValueError('Spoken note not found, or duplicate notes need resolving in Obsidian.')
        return found[0]

    def asset(self, note, relative, subfolder):
        if not isinstance(relative,str) or '\\' in relative or Path(relative).is_absolute():
            raise ValueError('Invalid spoken note attachment path.')
        path = self.workspace.safe(Path(note['path']).parent / relative)
        expected = Path(note['path']).parent / subfolder
        if path.parent != expected or path.name in {'', '.', '..'}:
            raise ValueError('Spoken note attachments must remain in their own folder.')
        return path

    def view(self, note):
        meta = note['meta']; fields = note['fields']; segments = [];latest_text='';latest_segments=[]
        transcripts = meta.get('transcripts', [])
        if not isinstance(transcripts,list):
            raise ValueError('Check the transcription history properties in Obsidian.')
        if transcripts:
            try:
                path = self.asset(note, transcripts[0]['path'], 'Transcripts')
                if path.stat().st_size <= 2_000_000:
                    data = json.loads(path.read_text(encoding='utf-8'))
                    segments = data.get('segments', [])
            except (OSError,ValueError,KeyError):
                segments = []
        if transcripts:
            try:
                latest=self.transcript(note,transcripts[-1]['id'])
                latest_text=latest.get('text','');latest_segments=latest.get('segments',[])
            except (OSError,ValueError,KeyError):pass
        return {'id':note['id'], 'paper_id':meta.get('paper_id'), 'section_id':meta.get('section_id'),
                'idea_id':meta.get('idea_id',''), 'title':note['title'], 'hash':note['hash'],
                'status':meta.get('status','saved'), 'error':meta.get('error',''),
                'created':meta.get('created'), 'updated':meta.get('updated'),
                'language':meta.get('speech_language','auto'), 'engine':meta.get('engine',''), 'model':meta.get('model',''),
                'duration_seconds':meta.get('duration_seconds',0), 'audio_bytes':meta.get('audio_bytes',0),
                'trashed':bool(meta.get('trashed',False)), 'trashed_at':meta.get('trashed_at',''),
                'merged_from':meta.get('merged_from',[]), 'original_text':fields.get(ORIGINAL,''),
                'corrected_text':fields.get(CORRECTED,''), 'ideas_text':fields.get(IDEAS,''), 'segments':segments,
                'latest_text':latest_text,'latest_segments':latest_segments,'transcripts':transcripts, 'audio_url':f"/api/workspace/papers/{quote(meta['paper_id'])}/voice-notes/{quote(note['id'])}/audio",
                'vault_path':note['vault_path'], 'uri':note['uri'], 'sync_message':SYNC}

    def transcript(self,note,transcript_id):
        identifier(transcript_id)
        records=[r for r in note['meta'].get('transcripts',[]) if r.get('id')==transcript_id]
        if len(records)!=1:raise ValueError('Transcript version not found.')
        path=self.asset(note,records[0]['path'],'Transcripts')
        if path.stat().st_size>2_000_000:raise ValueError('This transcript file is too large to open safely.')
        return json.loads(path.read_text(encoding='utf-8'))

    def list(self, paper_id, section_id=None, include_trashed=False):
        if section_id: identifier(section_id)
        notes=[]
        for path in self.folder(paper_id).glob('*.md'):
            note=self.read_path(path)
            if note['meta'].get('paper_id') == paper_id and (not section_id or note['meta'].get('section_id') == section_id) and (include_trashed or not note['meta'].get('trashed',False)):
                notes.append(self.view(note))
        return {'notes':sorted(notes,key=lambda n:str(n.get('created','')),reverse=True), 'sync_message':SYNC}

    def get(self, paper_id, note_id):
        return self.view(self.locate(paper_id,note_id))

    def revise(self, note, meta_changes=None, fields=None):
        """Keep every displaced Markdown file, including external edits arriving mid-save."""
        with self.workspace.lock:
            current = self.read_path(Path(note['path']))
            if current['hash'] != note['hash']:
                raise Conflict('These spoken notes changed elsewhere. Your changes are kept in the editor; reload and compare.', current=self.view(current))
            meta = {**current['meta'], **(meta_changes or {}), 'updated':now()}
            body=update_fields(current['_body'], fields or {})
            parsed=fields_of(body)
            if any(parsed.get(key)!=value.strip() for key,value in (fields or {}).items()):
                raise ValueError('Use ### for headings inside spoken notes. ## starts a separate note field; your editor changes are kept.')
            raw = frontmatter(meta) + body
            self.workspace.replace_note(Path(note['path']).parent, current, raw)
            return self.read_path(Path(note['path']))

    def edit(self, paper_id, note_id, body):
        with self.workspace.lock:
            note = self.locate(paper_id,note_id)
            if note['hash'] != body.base_hash:
                raise Conflict('These spoken notes changed elsewhere. Your corrections are kept in the editor; reload and compare.',current=self.view(note))
            note = self.revise(note, {'corrected_initialized':True}, {CORRECTED:body.corrected_text, IDEAS:body.ideas_text})
            return self.view(note)

    def decode(self, source, destination):
        decoder = self.runtime()['decoder']
        if not decoder:
            raise ValueError('Install the local audio decoder (FFmpeg) before saving audio. The browser recording is still available.')
        command=[str(decoder),'-nostdin','-hide_banner','-loglevel','error','-protocol_whitelist','file,pipe',
                 '-i',str(source),'-map','0:a:0','-vn','-t',str(MAX_SECONDS+1),'-ac','1','-ar','16000','-c:a','pcm_s16le','-y',str(destination)]
        try:
            result=subprocess.run(command,capture_output=True,timeout=45,check=False)
        except (OSError,subprocess.TimeoutExpired) as error:
            raise ValueError('The local decoder could not read this audio. Try a shorter WAV, M4A or WebM recording.') from error
        if result.returncode or not destination.is_file():
            raise ValueError('This file could not be decoded as audio. Choose a playable recording.')
        with wave.open(str(destination),'rb') as audio:
            duration=audio.getnframes()/audio.getframerate()
            samples=array('h',audio.readframes(audio.getnframes()))
            if sys.byteorder != 'little': samples.byteswap()
        if not 0.1 <= duration <= MAX_SECONDS:
            raise ValueError('Use a recording between a moment and 10 minutes long.')
        peak=max((abs(x) for x in samples),default=0)
        # Only truly silent / near-zero digital input bypasses recognition.
        silent=peak <= 16
        return duration,silent

    async def upload(self, paper_id, file, section_id, idea_id, title, speech_language, key, *, extra_metadata=None, extra_fields=None, validate_publish=None):
        identifier(section_id);request_key(key);language(speech_language)
        if len(idea_id)>150 or any(ord(c)<32 for c in idea_id): raise ValueError('Invalid outline idea.')
        section=self.workspace.card(paper_id,section_id)
        if section['type'] not in {'section','subsection','argument'}: raise ValueError('Choose a writing section or argument.')
        if len(title)>160 or '\n' in title or '\r' in title: raise ValueError('Use a short single-line title.')
        suffix=Path(file.filename or '').suffix.lower()
        if suffix not in EXTENSIONS: raise ValueError('Choose WAV, M4A, MP3, WebM, Ogg, FLAC, AAC or CAF audio.')
        self.local.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='voice-upload-',dir=self.local) as temporary:
            source=Path(temporary)/('input'+suffix); digest=hashlib.sha256(); size=0
            with source.open('wb') as stream:
                while chunk:=await file.read(1024*1024):
                    size+=len(chunk)
                    if size>MAX_UPLOAD: raise ValueError('This recording is too large. Keep audio below 40 MB.')
                    digest.update(chunk);stream.write(chunk)
            if not size:raise ValueError('The recording is empty. Record or choose an audio file first.')
            # Idempotency checks include bytes, so retry cannot silently reuse another recording.
            for path in self.folder(paper_id).glob('*.md'):
                note=self.read_path(path);meta=note['meta']
                if meta.get('request_key')==key:
                    if meta.get('audio_sha256')!=digest.hexdigest() or meta.get('section_id')!=section_id or meta.get('idea_id','')!=idea_id:
                        raise Conflict('This recording request key was already used for different audio.')
                    return self.view(note)
            duration,silent=await asyncio.to_thread(self.decode,source,Path(temporary)/'decoded.wav')
            with self.workspace.lock:
                if validate_publish:validate_publish()
                folder=self.folder(paper_id);folder.mkdir(parents=True,exist_ok=True)
                # Recheck after decoding in case another upload of the same recovery clip won.
                for path in folder.glob('*.md'):
                    note=self.read_path(path)
                    if note['meta'].get('request_key')==key:
                        if note['meta'].get('audio_sha256')!=digest.hexdigest():raise Conflict('Recording request key already used.')
                        return self.view(note)
                note_id=str(uuid.uuid4());created=now();title=title.strip() or 'Spoken idea'
                stem=portable_name(datetime.now().strftime('%Y-%m-%d %H%M%S')+' - '+section['title'][:55]+' - '+title[:55]+' - '+note_id[:8])
                audio=self.workspace.safe(folder/'Audio'/(stem+suffix));audio.parent.mkdir(parents=True,exist_ok=True)
                # Only publish completely written recordings, never a partial final attachment.
                fd, temporary_name=tempfile.mkstemp(prefix='.recording-',suffix='.tmp',dir=audio.parent)
                os.close(fd);temporary_audio=Path(temporary_name)
                try:
                    shutil.copyfile(source,temporary_audio)
                    with temporary_audio.open('rb') as stream:os.fsync(stream.fileno())
                    os.replace(temporary_audio,audio)
                finally:temporary_audio.unlink(missing_ok=True)
                metadata={'awl_schema':1,'awl_kind':'voice_note','awl_id':note_id,'paper_id':paper_id,'section_id':section_id,
                          'idea_id':idea_id,'title':title,'created':created,'updated':created,'status':'saved','speech_language':speech_language,
                          'engine':'','model':'','audio_relative_path':'Audio/'+audio.name,'audio_sha256':digest.hexdigest(),
                          'duration_seconds':round(duration,2),'audio_bytes':size,'trashed':False,'request_key':key,'transcripts':[], 'corrected_initialized':False,'original_initialized':False,'digital_silence':silent}
                metadata.update(extra_metadata or {})
                relative=os.path.relpath(section['path'],folder).replace(os.sep,'/')
                text=frontmatter(metadata)+'# '+title+'\n\nPrivate spoken notes, not a literature quotation or verified evidence.\n\n[Writing section]('+quote(relative)+') · [Play recording]('+quote('Audio/'+audio.name)+')\n\n'+SYNC+'\n\n'
                text=update_fields(text,{ORIGINAL:'',CORRECTED:'',IDEAS:'','Transcription history':'',**(extra_fields or {})})
                path=self.workspace.safe(folder/(stem+'.md'));atomic_write(path,text,exclusive=True)
                return self.view(self.read_path(path))

    def job_path(self, job_id):
        identifier(job_id)
        return self.local/'jobs'/(job_id+'.json')

    def save_job(self, job):
        atomic_write(self.job_path(job['id']),json.dumps(job,indent=2))

    async def transcribe(self, paper_id,note_id,body):
        request_key(body.request_key)
        with self.workspace.lock:
            note=self.locate(paper_id,note_id);meta=note['meta']
            if meta.get('trashed'):raise ValueError('Restore this recording from deleted recordings before transcribing it.')
            for previous in meta.get('transcription_requests',[]):
                if previous.get('request_key')==body.request_key:return self.view(note)
            if meta.get('status') in {'queued','transcribing'}:
                # A remote machine may still be working. Never steal a running job.
                return self.view(note)
            if not self.status()['ready']:raise ValueError(self.status()['message'])
            lang=language(body.language or meta.get('speech_language','auto'))
            job={'id':str(uuid.uuid4()),'paper_id':paper_id,'note_id':note_id,'request_key':body.request_key,'language':lang,'created':now(),'status':'queued'}
            self.save_job(job)
            history=[*meta.get('transcription_requests',[]),{'request_key':body.request_key,'job_id':job['id']}]
            note=self.revise(note,{'status':'queued','error':'','job_id':job['id'],'speech_language':lang,'transcription_requests':history})
            self.tasks[job['id']]=asyncio.create_task(self.run(job))
            return self.view(note)

    def update_job_note(self,job,changes,fields=None):
        with self.workspace.lock:
            note=self.locate(job['paper_id'],job['note_id'])
            if note['meta'].get('job_id')!=job['id']:return None
            return self.revise(note,changes,fields)

    async def run(self,job):
        process=None
        try:
            async with self.lab.semaphore:
                job['status']='transcribing';self.save_job(job)
                note=self.update_job_note(job,{'status':'transcribing','error':''})
                if not note:return
                if note['meta'].get('trashed'):raise ValueError('This recording is in deleted recordings. Restore it before transcribing.')
                runtime=self.runtime()
                if not all(runtime.values()):raise ValueError(self.status()['message'])
                audio=self.asset(note,note['meta']['audio_relative_path'],'Audio')
                if not audio.is_file():raise ValueError('The audio attachment has not arrived. Let Obsidian Sync finish, then retry.')
                if not 0<audio.stat().st_size<=MAX_UPLOAD:raise ValueError('Keep the recording below 40 MB before transcribing.')
                if hashlib.sha256(audio.read_bytes()).hexdigest()!=note['meta'].get('audio_sha256'):
                    raise ValueError('The audio attachment changed. Keep it and import it as a new spoken note.')
                with tempfile.TemporaryDirectory(prefix='transcribe-',dir=self.local) as temporary:
                    wav=Path(temporary)/'speech.wav';duration,silent=await asyncio.to_thread(self.decode,audio,wav)
                    text='';segments=[];actual_language=job['language']
                    if not silent:
                        output=Path(temporary)/'transcript'
                        command=[str(runtime['engine']),'-m',str(runtime['model']),'-f',str(wav),'-l',job['language'],'-oj','-of',str(output),'-t','4']
                        process=await asyncio.create_subprocess_exec(*command,stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.PIPE)
                        self.processes[job['id']]=process
                        _,error=await asyncio.wait_for(process.communicate(),timeout=900)
                        if process.returncode or not output.with_suffix('.json').is_file():
                            raise ValueError('Local transcription did not finish. Your audio is saved; retry or check the speech installation.')
                        if output.with_suffix('.json').stat().st_size>2_000_000:
                            raise ValueError('The speech engine returned an unexpectedly large transcript. Your audio is saved.')
                        data=json.loads(output.with_suffix('.json').read_text(encoding='utf-8'))
                        actual_language=data.get('result',{}).get('language',job['language'])
                        for segment in data.get('transcription',[]):
                            item=segment.get('text','').strip();offsets=segment.get('offsets',{})
                            if not item:continue
                            start=max(0,float(offsets.get('from',0))/1000);end=min(duration,float(offsets.get('to',0))/1000)
                            if not 0<=start<=end<=duration:raise ValueError('The speech engine returned invalid timestamps. Your audio is saved.')
                            segments.append({'start':round(start,3),'end':round(end,3),'text':item})
                        text=' '.join(s['text'] for s in segments).strip()
                        if len(text)>100000:raise ValueError('The transcript is unexpectedly long. Your audio is saved.')
                    with self.workspace.lock:
                        current=self.locate(job['paper_id'],job['note_id'])
                        if current['meta'].get('job_id')!=job['id'] or current['meta'].get('status')=='cancelled' or current['meta'].get('trashed'):return
                        created=now();relative='Transcripts/'+job['note_id']+'-'+job['id']+'.json'
                        transcript={'id':job['id'],'created':created,'engine':'whisper.cpp','model':runtime['model'].name,'language':actual_language,'text':text,'segments':segments,'no_speech_detected':silent or not text}
                        path=self.asset(current,relative,'Transcripts');atomic_write(path,json.dumps(transcript,ensure_ascii=False,indent=2),exclusive=True)
                        records=[*current['meta'].get('transcripts',[]),{k:transcript[k] for k in ('id','created','engine','model','language')}|{'path':relative}]
                        updates={}
                        if not current['meta'].get('transcripts') and not current['meta'].get('original_initialized') and not current['fields'].get(ORIGINAL,'').strip():updates[ORIGINAL]=text
                        if not current['meta'].get('corrected_initialized') and not current['fields'].get(CORRECTED,'').strip():updates[CORRECTED]=text
                        updates['Transcription history']='\n'.join('- ['+r['created']+' · '+r.get('model','')+']('+quote(r['path'])+')' for r in records)
                        changes={'status':'complete','error':'No speech detected. Your recording is kept for playback.' if not text else '',
                                 'engine':'whisper.cpp','model':runtime['model'].name,'transcripts':records,'corrected_initialized':True,'original_initialized':True}
                        self.revise(current,changes,updates)
                        job['status']='complete';self.save_job(job)
        except asyncio.CancelledError:
            if process and process.returncode is None:
                process.kill();await process.wait()
            job['status']='cancelled';self.save_job(job)
            try:self.update_job_note(job,{'status':'cancelled','error':'Transcription stopped. Your recording and notes are saved.'})
            except (OSError,ValueError):pass
        except Exception as error:
            if process and process.returncode is None:
                process.kill();await process.wait()
            job['status']='failed';job['error']=str(error)[:1000];self.save_job(job)
            try:self.update_job_note(job,{'status':'failed','error':str(error)[:1000]})
            except (OSError,ValueError):pass
        finally:
            self.tasks.pop(job['id'],None);self.processes.pop(job['id'],None)

    async def cancel(self,paper_id,note_id):
        note=self.locate(paper_id,note_id);job_id=note['meta'].get('job_id')
        if job_id in self.tasks:
            self.revise(note,{'status':'cancelled','error':'Transcription stopped. Your recording and notes are saved.'})
            try:
                job=json.loads(self.job_path(job_id).read_text());job['status']='cancelled';self.save_job(job)
            except (OSError,ValueError):pass
            task=self.tasks[job_id];task.cancel()
            await asyncio.gather(task,return_exceptions=True)
            self.tasks.pop(job_id,None);self.processes.pop(job_id,None)
        elif note['meta'].get('status') in {'queued','transcribing'}:
            # A running job on another device cannot be killed here. Mark local cancellation;
            # its output is kept separately and cannot overwrite author-corrected notes.
            self.revise(note,{'status':'cancelled','error':'Cancellation recorded here. If another device is transcribing, stop it there too.'})
        return self.get(paper_id,note_id)

    async def trash(self,paper_id,note_id):
        await self.cancel(paper_id,note_id)
        with self.workspace.lock:
            note=self.locate(paper_id,note_id)
            if not note['meta'].get('trashed'):
                note=self.revise(note,{'trashed':True,'trashed_at':now()})
            return self.view(note)

    def restore(self,paper_id,note_id):
        with self.workspace.lock:
            note=self.locate(paper_id,note_id)
            if note['meta'].get('trashed'):
                note=self.revise(note,{'trashed':False,'trashed_at':''})
            return self.view(note)

    def merge_sources(self,paper_id,note_ids):
        if len(note_ids)!=len(set(note_ids)):
            raise ValueError('Choose each recording only once for a merge.')
        notes=[self.locate(paper_id,identifier(note_id)) for note_id in note_ids]
        if len({n['meta'].get('section_id') for n in notes})!=1:
            raise ValueError('Merge recordings from the same paper section or argument.')
        if any(n['meta'].get('trashed') for n in notes):
            raise ValueError('Restore deleted recordings before merging them.')
        return notes

    @staticmethod
    def merge_signature(notes):
        value={'section_id':notes[0]['meta']['section_id'],
               'sources':[{'id':n['id'],'audio_sha256':n['meta'].get('audio_sha256','')} for n in notes]}
        return sha(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False))

    def existing_merge(self,paper_id,key,signature):
        for path in self.folder(paper_id).glob('*.md'):
            note=self.read_path(path)
            if key in {note['meta'].get('request_key'),note['meta'].get('merge_request_key')}:
                if note['meta'].get('merge_signature')!=signature:
                    raise Conflict('This merge request key was already used for another recording order or audio version.')
                return self.view(note)
        return None

    def verify_merge_audio(self,notes):
        for note in notes:
            audio=self.asset(note,note['meta'].get('audio_relative_path'),'Audio')
            if not audio.is_file():raise ValueError('A recording attachment has not arrived. Let Obsidian Sync finish before merging.')
            if not 0<audio.stat().st_size<=MAX_UPLOAD:raise ValueError('Each recording must be below 40 MB.')
            if hashlib.sha256(audio.read_bytes()).hexdigest()!=note['meta'].get('audio_sha256'):
                raise Conflict('A source recording changed. Reload the recordings before merging.')

    def encode_merge(self,notes,directory):
        total=0.0;wav=directory/'joined.wav'
        with wave.open(str(wav),'wb') as joined:
            joined.setnchannels(1);joined.setsampwidth(2);joined.setframerate(16000)
            for index,note in enumerate(notes):
                audio=self.asset(note,note['meta']['audio_relative_path'],'Audio')
                snapshot=directory/('source-'+str(index)+audio.suffix)
                if not audio.is_file():raise ValueError('A recording is still syncing. Wait for its attachment, then retry.')
                if not 0<audio.stat().st_size<=MAX_UPLOAD:raise ValueError('Each recording must be below 40 MB.')
                shutil.copyfile(audio,snapshot)
                if hashlib.sha256(snapshot.read_bytes()).hexdigest()!=note['meta'].get('audio_sha256'):
                    raise Conflict('A source recording changed. Reload it before merging.')
                decoded=directory/('decoded-'+str(index)+'.wav')
                duration,_=self.decode(snapshot,decoded);total+=duration
                if total>MAX_SECONDS:raise ValueError('The combined recording must be at most 10 minutes. Choose fewer clips.')
                with wave.open(str(decoded),'rb') as source:
                    if source.getnchannels()!=1 or source.getsampwidth()!=2 or source.getframerate()!=16000:
                        raise ValueError('Audio could not be converted to the format needed for merging.')
                    while frames:=source.readframes(16000):joined.writeframesraw(frames)
        decoder=self.runtime()['decoder']
        if not decoder:raise ValueError('Install FFmpeg before merging recordings.')
        output=directory/'merged.m4a'
        command=[str(decoder),'-nostdin','-hide_banner','-loglevel','error','-i',str(wav),'-map_metadata','-1',
                 '-c:a','aac','-b:a','64k','-movflags','+faststart','-y',str(output)]
        try:result=subprocess.run(command,capture_output=True,timeout=90,check=False)
        except (OSError,subprocess.TimeoutExpired) as error:
            raise ValueError('The recordings could not be combined. Your originals are unchanged.') from error
        if result.returncode or not output.is_file() or not 0<output.stat().st_size<=MAX_UPLOAD:
            raise ValueError('The combined recording could not be saved below 40 MB. Your originals are unchanged.')
        return output

    async def merge(self,paper_id,body):
        request_key(body.request_key);lang=language(body.language)
        if '\n' in body.title or '\r' in body.title:raise ValueError('Use a short single-line title.')
        async with self.merge_lock:
            notes=self.merge_sources(paper_id,body.note_ids);signature=self.merge_signature(notes)
            await asyncio.to_thread(self.verify_merge_audio,notes)
            previous=self.existing_merge(paper_id,body.request_key,signature)
            if previous:return previous
            if not self.runtime()['decoder']:raise ValueError('Install FFmpeg before merging recordings.')
            self.local.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='voice-merge-',dir=self.local) as temporary:
                output=await asyncio.to_thread(self.encode_merge,notes,Path(temporary))
                latest=self.merge_sources(paper_id,body.note_ids)
                if self.merge_signature(latest)!=signature:
                    raise Conflict('A source recording changed while merging. Your originals are unchanged; reload and retry.')
                await asyncio.to_thread(self.verify_merge_audio,latest)
                # Upload performs the same final decode, size checks and durable audio
                # publication as a microphone recording before any transcription runs.
                sources=[{'id':n['id'],'title':n['title'],'audio_sha256':n['meta']['audio_sha256']} for n in notes]
                folder=self.folder(paper_id)
                links='\n'.join(str(i+1)+'. ['+n['title'].replace('[','(').replace(']',')')+']('+quote(os.path.relpath(n['path'],folder).replace(os.sep,'/'))+')' for i,n in enumerate(notes))
                def validate_publish():
                    current=self.merge_sources(paper_id,body.note_ids)
                    if self.merge_signature(current)!=signature:
                        raise Conflict('A source recording changed before the merge was saved. Reload and retry.')
                    self.verify_merge_audio(current)
                with output.open('rb') as stream:
                    uploaded=UploadFile(stream,filename='merged.m4a')
                    return await self.upload(paper_id,uploaded,notes[0]['meta']['section_id'],'',body.title,lang,body.request_key,
                        extra_metadata={'merged_from':sources,'merge_request_key':body.request_key,'merge_signature':signature},
                        extra_fields={'Merged recordings':'Original recordings are kept. This audio joins them in the following order; the transcript is created separately.\n\n'+links},
                        validate_publish=validate_publish)

    def recover(self):
        for path in (self.local/'jobs').glob('*.json'):
            try:
                job=json.loads(path.read_text(encoding='utf-8'))
                if job.get('status') not in {'queued','transcribing'}:continue
                self.update_job_note(job,{'status':'failed','error':'The app restarted during transcription. Your recording is saved; retry when ready.'})
                job['status']='failed';self.save_job(job)
            except (OSError,ValueError,KeyError):continue

    async def close(self):
        for job_id,task in list(self.tasks.items()):
            try:
                job=json.loads(self.job_path(job_id).read_text())
                await self.cancel(job['paper_id'],job['note_id'])
            except (OSError,ValueError,KeyError):
                task.cancel();await asyncio.gather(task,return_exceptions=True)


def voice_router(service):
    router=APIRouter()
    base='/api/workspace/papers/{paper_id}/voice-notes'

    @router.get('/api/voice/status')
    def status():return service.status()

    @router.get(base)
    def notes(paper_id:str,section_id:str|None=None,include_trashed:bool=False):return service.list(paper_id,section_id,include_trashed)

    @router.post(base)
    async def upload(paper_id:str,file:UploadFile=File(...),section_id:str=Form(...),idea_id:str=Form(''),title:str=Form(''),language:str=Form('auto'),request_key:str=Form(...),transcribe:bool=Form(False)):
        try:note=await service.upload(paper_id,file,section_id,idea_id,title,language,request_key)
        finally:await file.close()
        if transcribe and service.status()['ready']:
            return await service.transcribe(paper_id,note['id'],TranscribeVoice(request_key=request_key+'-transcribe',language=language))
        return note

    @router.post(base+'/merge')
    async def merge(paper_id:str,body:MergeVoice):return await service.merge(paper_id,body)

    @router.post(base+'/{note_id}/trash')
    async def trash(paper_id:str,note_id:str):return await service.trash(paper_id,note_id)

    @router.post(base+'/{note_id}/restore')
    def restore(paper_id:str,note_id:str):return service.restore(paper_id,note_id)

    @router.get(base+'/{note_id}')
    def note(paper_id:str,note_id:str):return service.get(paper_id,note_id)

    @router.patch(base+'/{note_id}')
    def edit(paper_id:str,note_id:str,body:EditVoice):return service.edit(paper_id,note_id,body)

    @router.post(base+'/{note_id}/transcribe')
    async def transcribe(paper_id:str,note_id:str,body:TranscribeVoice):return await service.transcribe(paper_id,note_id,body)

    @router.post(base+'/{note_id}/cancel')
    async def cancel(paper_id:str,note_id:str):return await service.cancel(paper_id,note_id)

    @router.get(base+'/{note_id}/transcripts/{transcript_id}')
    def transcript(paper_id:str,note_id:str,transcript_id:str):
        return service.transcript(service.locate(paper_id,note_id),transcript_id)

    @router.get(base+'/{note_id}/audio')
    def audio(paper_id:str,note_id:str):
        note=service.locate(paper_id,note_id)
        path=service.asset(note,note['meta'].get('audio_relative_path'),'Audio')
        if not path.is_file():raise ValueError('Waiting for the recording attachment. Let Obsidian Sync finish.')
        return FileResponse(path,media_type=MEDIA.get(path.suffix.lower(),'application/octet-stream'),filename=path.name,content_disposition_type='inline')

    return router
