"""Preview or import a card ZIP into an existing, configured Obsidian paper."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.workspace import Workspace
from backend.outline_import import prepare, apply


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault',required=True,type=Path)
    parser.add_argument('--data-dir',required=True,type=Path)
    parser.add_argument('--paper-id',required=True)
    parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--label',required=True)
    parser.add_argument('--apply',action='store_true',help='Import and activate the converted outline. Stop the app first.')
    args = parser.parse_args()
    workspace = Workspace(SimpleNamespace(vault=args.vault.resolve(),store=SimpleNamespace(directory=args.data_dir.resolve())))
    prepared = prepare(workspace,args.paper_id,args.archive.read_bytes(),args.label)
    if args.apply:
        result = apply(workspace,prepared)
    elif prepared['already_imported']:
        result = {**prepared['receipt'],'already_imported':True}
    else:
        result = {'label':prepared['label'],'paper_id':args.paper_id,'base_hash':prepared['base_hash'],
                  'arguments':sum(c['meta']['card_type']=='argument' for c in prepared['cards'].values()),
                  'sections':sum(c['meta']['card_type']=='section' for c in prepared['cards'].values()),
                  'material_files':len(prepared['files'])-len(prepared['cards'])-1,'applied':False}
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
