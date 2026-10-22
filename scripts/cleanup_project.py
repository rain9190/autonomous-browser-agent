"""Archive known milestone notes; remove generated caches. Dry run unless --apply."""
import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess

HISTORICAL=(
    'README-ACTION-CATALOG.md','README-BENCHMARK-LINKS.md','README-CHANGED-ID.md',
    'README-COMPARISON.md','README-CONTROLLED-TIMEOUT.md','README-DAY2.md',
    'README-EVALUATION.md','README-FULL-CREDIT.md','README-NEXT.md','README-ONESHOT.md',
    'README-PROGRESS.md','README-RECOVERY-ABLATION.md','README-RECOVERY-EVALUATION.md',
    'README-RECOVERY.md','README-SELECTION.md','README-SEVEN-STEP.md',
    'README-SIMPLE-VARIANTS.md','README-TABS.md','README-TEXT-ENTRY.md',
    'day2.gitignore','requirements-day2.txt',
)
SOURCE_DIRS=('app','browser_agent','extension_service','form_assistant','scripts','tests','website_trial')

@dataclass(frozen=True)
class Action:
    kind:str
    source:Path
    destination:Path|None=None


def tracked_files(root):
    result=subprocess.run(['git','ls-files','-z'],cwd=root,check=True,capture_output=True)
    return {Path(os.fsdecode(name)) for name in result.stdout.split(b'\0') if name}


def plan(root,tracked=None):
    root=Path(root).resolve()
    if not (root/'extension/manifest.json').is_file() or not (root/'browser_agent').is_dir():
        raise ValueError('Run this only inside the autonomous-browser-agent repository')
    if not (root/'requirements.txt').is_file():
        raise ValueError('Install the final documentation update, including requirements.txt, first')
    tracked=tracked_files(root) if tracked is None else set(map(Path,tracked))
    frozen_manifest=root/'docs/benchmark/freeze-manifest.json'
    frozen=set(map(Path,json.loads(frozen_manifest.read_text()).get('file_sha256',{}))) if frozen_manifest.is_file() else set()
    def protected(path,include_tracked=True):
        relative=path.relative_to(root)
        return any(p==relative or relative in p.parents for p in (frozen|tracked if include_tracked else frozen))
    actions=[]
    history=root/'docs/history'
    for parent in (root/'docs',history):
        if parent.is_symlink():raise ValueError('History directory must not be a symbolic link')
    for name in HISTORICAL:
        source=root/name;destination=history/name
        if not source.exists():continue
        if source.is_symlink() or not source.is_file() or protected(source,False):raise ValueError('Historical file cannot be moved: '+name)
        if name=='requirements-day2.txt' and source.read_bytes()!=(root/'requirements.txt').read_bytes():
            raise ValueError('Dependency files differ; keep requirements-day2.txt until reviewed')
        if destination.exists() or destination.is_symlink():raise ValueError('Archive destination already exists: '+name)
        actions.append(Action('archive',source,destination))
    candidates=[]
    for name in SOURCE_DIRS:
        folder=root/name
        if not folder.is_dir() or folder.is_symlink():continue
        for current,dirs,files in os.walk(folder,followlinks=False):
            base=Path(current)
            dirs[:]=[d for d in dirs if not (base/d).is_symlink()]
            if '__pycache__' in dirs:
                candidates.append(base/'__pycache__');dirs.remove('__pycache__')
            candidates.extend(base/f for f in files if (f.endswith('.pyc') or f=='.DS_Store') and not (base/f).is_symlink())
    candidates.extend(root/name for name in ('.pytest_cache','.DS_Store') if (root/name).exists() and not (root/name).is_symlink())
    for path in sorted(set(candidates)):
        if not protected(path):actions.append(Action('cache',path))
    return actions


def apply(actions):
    # All moves/conflicts/protected paths are validated before the first mutation.
    for action in actions:
        if action.kind=='archive':
            action.destination.parent.mkdir(parents=True,exist_ok=True)
            action.source.rename(action.destination)
        elif action.source.is_dir():shutil.rmtree(action.source)
        else:action.source.unlink()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    try:actions=plan(root)
    except (ValueError,OSError,subprocess.CalledProcessError,json.JSONDecodeError) as error:
        parser.exit(1,'Cleanup stopped: '+str(error)+'\n')
    for action in actions:
        print(('Archive ' if action.kind=='archive' else 'Remove generated cache ')+str(action.source.relative_to(root)))
    if args.apply:apply(actions)
    print(('Completed: ' if args.apply else 'Preview only: ')+str(sum(a.kind=='archive' for a in actions))+' historical files, '+str(sum(a.kind=='cache' for a in actions))+' cache paths.')
    if not args.apply:print('Run with --apply to perform exactly this cleanup.')

if __name__=='__main__':main()
