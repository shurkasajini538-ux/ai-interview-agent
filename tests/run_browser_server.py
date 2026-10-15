"""Serve an isolated temporary workspace for browser acceptance tests."""
import os
import shutil
import sys
import tempfile
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Studio, handler_factory

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='interview-browser-test-') as temporary:
    directory = Path(temporary)
    shutil.copytree(root/'web', directory/'web')
    shutil.copytree(root/'samples', directory/'samples')
    if (root/'frontend'/'dist').exists():
        shutil.copytree(root/'frontend'/'dist',directory/'frontend'/'dist')
    server = ThreadingHTTPServer(('127.0.0.1', int(os.environ.get('STUDIO_TEST_PORT', '8766'))), handler_factory(Studio(directory)))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
