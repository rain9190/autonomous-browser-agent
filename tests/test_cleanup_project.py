from pathlib import Path
import json
import pytest
from scripts.cleanup_project import plan,apply


def project(tmp_path):
    (tmp_path/'extension').mkdir();(tmp_path/'extension/manifest.json').write_text('{}')
    (tmp_path/'browser_agent').mkdir();(tmp_path/'requirements.txt').write_text('example==1\n')
    return tmp_path


def test_dry_run_then_archive_and_remove_only_generated_paths(tmp_path):
    root=project(tmp_path);old=root/'README-DAY2.md';old.write_text('historical')
    (root/'requirements-day2.txt').write_text('example==1\n')
    cache=root/'browser_agent/__pycache__';cache.mkdir();(cache/'agent.pyc').write_bytes(b'cache')
    source=root/'browser_agent/agent.py';source.write_text('print("keep")')
    actions=plan(root,tracked={Path('browser_agent/agent.py')})
    assert old.exists() and cache.exists() # planning is read-only
    apply(actions)
    assert (root/'docs/history/README-DAY2.md').read_text()=='historical'
    assert (root/'requirements.txt').exists() and not cache.exists() and source.exists()
    assert plan(root,tracked={Path('browser_agent/agent.py')})==[]


def test_vendor_environment_results_and_symlink_targets_are_untouched(tmp_path):
    root=project(tmp_path)
    for name in ('.venv','vendor','results'):
        p=root/name/'__pycache__';p.mkdir(parents=True);(p/'keep.pyc').write_bytes(b'keep')
    (root/'.env.local').write_text('private fixture, not a real credential')
    outside=tmp_path.parent/(tmp_path.name+'-outside');outside.mkdir();(outside/'keep.pyc').write_bytes(b'keep')
    (root/'browser_agent/linked').symlink_to(outside,target_is_directory=True)
    assert plan(root,tracked=set())==[]
    assert (outside/'keep.pyc').exists() and (root/'.env.local').exists()


def test_tracked_and_frozen_cache_paths_are_not_removed(tmp_path):
    root=project(tmp_path)
    cache=root/'browser_agent/__pycache__';cache.mkdir();(cache/'tracked.pyc').write_bytes(b'keep')
    assert plan(root,tracked={Path('browser_agent/__pycache__/tracked.pyc')})==[]
    folder=root/'docs/benchmark';folder.mkdir(parents=True)
    (folder/'freeze-manifest.json').write_text(json.dumps({'file_sha256':{'browser_agent/__pycache__/tracked.pyc':'hash'}}))
    assert plan(root,tracked=set())==[]


def test_archive_conflict_or_changed_dependencies_stops_before_changes(tmp_path):
    root=project(tmp_path);(root/'README-DAY2.md').write_text('old')
    (root/'docs/history').mkdir(parents=True);(root/'docs/history/README-DAY2.md').write_text('different')
    with pytest.raises(ValueError,match='destination'):plan(root,tracked=set())
    assert (root/'README-DAY2.md').read_text()=='old'
    (root/'docs/history/README-DAY2.md').unlink()
    (root/'requirements-day2.txt').write_text('different==2')
    with pytest.raises(ValueError,match='Dependency'):plan(root,tracked=set())
    assert (root/'README-DAY2.md').exists()
