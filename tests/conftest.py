"""Keep the ASGI module's default app away from the learner's data during collection."""
import atexit
import os
import tempfile
from pathlib import Path

_default_workspace=tempfile.TemporaryDirectory(prefix='awl-test-default-')
atexit.register(_default_workspace.cleanup)
os.environ['AWL_DATA_DIR']=str(Path(_default_workspace.name)/'data')
os.environ['AWL_VAULT']=str(Path(_default_workspace.name)/'vault')
