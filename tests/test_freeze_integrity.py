"""Fail closed on modified frozen source; no API/browser work."""
import json
import pytest
from scripts.check_benchmark_plan import verify


def test_tampered_source_stops_before_runtime_imports(tmp_path):
    folder = tmp_path / 'docs/benchmark'
    folder.mkdir(parents=True)
    source = tmp_path / 'frozen.py'
    source.write_text('changed')
    (folder/'freeze-manifest.json').write_text(json.dumps({'file_sha256': {'frozen.py': '0'*64}}))
    with pytest.raises(ValueError, match='Frozen file changed: frozen.py'):
        verify(tmp_path)
