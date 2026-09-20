"""Exercise a fresh installation and a copied vault, using temporary data only.

This is an API/storage smoke check, not a test of Obsidian's remote Sync service
or a real Ollama model. It is intended to run on each supported OS in CI.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile


def check_installation():
    with tempfile.TemporaryDirectory(prefix='Writing Lab café ') as temporary:
        root=Path(temporary)
        first=root/'Device one – café'
        second=root/'Device two – książka'
        for device in (first,second):
            (device/'Obsidian vault'/'.obsidian').mkdir(parents=True)
        first_vault=first/'Obsidian vault'
        private_library=first_vault/'06_Academic_Writing_Lab'/'Private library'
        private_library.mkdir(parents=True)
        blueprint={'nodes':[],'sections':{},'title':'Smoke-test library',
                   'books':[{'id':'SMOKE-STYLE','path':r'C:\Previous device\private fixture.pdf'}]}
        reading_path='Materials/Clarity – przykład.pdf'
        mapping={'version':1,'readings':{'SMOKE-STYLE':reading_path}}
        for title,value in (('Paper blueprint.md',blueprint),('Reading attachments.md',mapping)):
            (private_library/title).write_text('# Private test fixture\n\n```json\n'+
                                               json.dumps(value,ensure_ascii=False)+'\n```\n',encoding='utf-8')
        # A minimal one-page PDF: only synthetic bytes enter the fixture vault.
        pdf=b'%PDF-1.4\n'
        offsets=[0]
        objects=(b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                 b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >>')
        for number,body in enumerate(objects,1):
            offsets.append(len(pdf));pdf+=str(number).encode()+b' 0 obj\n'+body+b'\nendobj\n'
        xref=len(pdf)
        pdf+=b'xref\n0 4\n0000000000 65535 f \n'+b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
        pdf+=b'trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n'
        attachment=first_vault/reading_path;attachment.parent.mkdir(parents=True);attachment.write_bytes(pdf)
        # Importing main constructs its default ASGI app. Keep that instance,
        # too, away from any existing installation or selected personal vault.
        os.environ['AWL_DATA_DIR']=str(root/'Unused default data')
        os.environ['AWL_VAULT']=str(root/'Unused default vault')
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        from fastapi.testclient import TestClient
        from backend.main import create_app

        def request(client,method,path,**kwargs):
            response=client.request(method,path,**kwargs)
            assert response.status_code==200,(method,path,response.status_code,response.text)
            return response.json()

        def connect(client,vault):
            bootstrap=request(client,'GET','/api/bootstrap')
            client.headers['X-AWL-Token']=bootstrap['token']
            request(client,'POST','/api/workspace/configure',json={'vault':str(vault)})
            return bootstrap

        prose='The café study records waiting time; it does not establish causality. α → β.'
        notes='Sprawdź zakres: preserve the distinction between observation and explanation.'
        outline='## Section: Introduction\n### Argument: What the café observations show\n- Describe the observation\n- Keep the limitation\n'
        app=create_app(first/'Local application data',first/'Obsidian vault',auto_tutor=False)
        with TestClient(app,base_url='http://127.0.0.1') as client:
            first_health=request(client,'GET','/api/health')
            assert client.get('/').status_code==200
            connect(client,first/'Obsidian vault')
            reading=client.get('/api/paper/readings/SMOKE-STYLE')
            assert reading.status_code==200 and reading.content==pdf
            assert client.get('/api/paper/readings/unregistered-smoke-reading').status_code==404
            for path in ('/api/workspace/section-writing-guide','/api/workspace/section-template',
                         '/api/workspace/manual-paper-guide','/api/obsidian/guide','/api/guides/portable'):
                assert client.get(path).status_code==200,path
            speech=request(client,'GET','/api/voice/status')
            assert speech['max_duration_seconds']==600
            paper=request(client,'POST','/api/workspace/papers',json={'title':'Café – bounded observations','outline':outline})
            argument=next(node for node in paper['nodes'] if node['type']=='argument')
            section=next(node for node in paper['nodes'] if node['type']=='section')
            card_url=f"/api/workspace/papers/{paper['id']}/cards/{argument['id']}"
            note=request(client,'GET',card_url)
            saved=request(client,'PATCH',f"/api/workspace/papers/{paper['id']}/notes/{argument['id']}",
                          json={'base_hash':note['hash'],'fields':{'Manuscript prose':prose,'Reasoning and decisions':notes}})
            section_url=f"/api/workspace/papers/{paper['id']}/sections/{section['id']}/writing"
            assert request(client,'GET',section_url)['section']['id']==section['id']
            key='AWL-EN-CORE@2:AWL-EN-F01-Q01'
            answer=request(client,'POST','/api/submit',json={'exercise_key':key,'text':'require',
                           'request_key':'portable-smoke-answer','reason':'The plural subject requires the plural verb.'})
            assert answer['correct'] is True
            assert request(client,'GET','/api/courses')['exercise_status'][key]['completed']
            assert request(client,'POST','/api/workspace/sync')['state']=='saved'

        # Copy files as a completed sync would; never copy a running database.
        shutil.copytree(first/'Obsidian vault',second/'Obsidian vault',dirs_exist_ok=True)
        assert not list((second/'Obsidian vault').rglob('*.sqlite3*'))
        reopened=create_app(second/'Local application data',second/'Obsidian vault',auto_tutor=False)
        with TestClient(reopened,base_url='http://127.0.0.1') as client:
            second_health=request(client,'GET','/api/health')
            assert first_health['instance_id']!=second_health['instance_id']
            connect(client,second/'Obsidian vault')
            reading=client.get('/api/paper/readings/SMOKE-STYLE')
            assert reading.status_code==200 and reading.content==pdf
            assert reading.headers['content-type']=='application/pdf'
            assert client.get('/api/paper/readings/unregistered-smoke-reading').status_code==404
            assert request(client,'POST','/api/workspace/sync')['state']=='saved'
            restored=request(client,'GET',card_url)
            assert restored['fields']['Manuscript prose']==prose
            assert restored['fields']['Reasoning and decisions']==notes
            assert restored['hash']==saved['hash']
            assert Path(restored['path']).resolve().is_relative_to((second/'Obsidian vault').resolve())
            assert request(client,'GET',section_url)['section']['id']==section['id']
            session=request(client,'GET','/api/sessions/'+answer['session_id'])
            assert session['text']=='require' and len(session['attempts'])==1
            assert request(client,'GET','/api/courses')['exercise_status'][key]['completed']
            assert request(client,'POST','/api/workspace/sync')['state']=='saved'
            assert request(client,'GET','/api/progress')['attempts']==1
            export=client.get(f"/api/workspace/papers/{paper['id']}/export")
            assert export.status_code==200 and prose in export.text and notes not in export.text

        return {'status':'passed','os':platform.system(),'python':platform.python_version(),
                'app_version':first_health['version'],
                'checks':['fresh API startup','spaces and Unicode in paths and text','paper and section reopen',
                          'private mapped PDF reopens from the copied vault',
                          'copied-vault prose and reasoning','saved answer and completion restore',
                          'repeat sync without duplicate attempts','manuscript export excludes notes'],
                'limits':['remote Obsidian Sync not exercised','local model inference not exercised',
                          'desktop shortcut UI not exercised']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Optional JSON report, containing no personal records.')
    args=parser.parse_args()
    result=check_installation()
    raw=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(raw,encoding='utf-8')
    print(raw,end='')
