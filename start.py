"""Start the writing lab without exposing it to the network."""
import argparse
import json
import threading
import urllib.request
import webbrowser
import uvicorn

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--reload', action='store_true')
    parser.add_argument('--open', action='store_true', help='Open the local app in your browser.')
    args = parser.parse_args()
    if args.open:
        url=f'http://127.0.0.1:{args.port}'
        try:
            with urllib.request.urlopen(url+'/api/health',timeout=2) as response:
                running=json.load(response)
            if running.get('mode')=='local' and running.get('status')=='ok':
                webbrowser.open(url)
                raise SystemExit(0)
        except (OSError,ValueError):pass
        threading.Timer(2,lambda:webbrowser.open(url)).start()
    uvicorn.run('backend.main:app', host='127.0.0.1', port=args.port, reload=args.reload)
