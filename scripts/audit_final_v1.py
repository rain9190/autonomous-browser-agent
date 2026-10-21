"""Offline audit/export of the frozen v1 results. Never executes agent episodes."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root, output):
    require(not output.exists(), 'Output already exists; preserve earlier audit')
    subprocess.run([sys.executable, '-B', str(root/'scripts/check_benchmark_plan.py')], cwd=root, check=True)
    sys.path.insert(0, str(root))
    from browser_agent.compare import summarize_pairs
    from browser_agent.ablate_recovery import summarize, matching_failures
    plan = read(root/'docs/benchmark/task-plan.json')
    schedule = read(root/'docs/benchmark/final-batches.json')['batches']
    manifest = read(root/'docs/benchmark/freeze-manifest.json')
    source = {Path(p).name: h for p,h in manifest['file_sha256'].items() if p.startswith('browser_agent/')}
    package_versions = {p: manifest['package_versions'][p] for p in ['openai','langgraph','pydantic','browsergym-core','browsergym-miniwob']}
    candidates = defaultdict(list)
    for folder in sorted((root/'results').iterdir()):
        config_path = folder/'config.json'
        if not config_path.is_file(): continue
        cfg = read(config_path)
        if cfg.get('seeds') != plan['reserved_final_seeds']: continue
        arms = cfg.get('arms')
        kind = 'planning' if arms == ['oneshot','iterative'] else 'recovery' if arms == ['recovery_off','recovery_on'] else None
        require(kind is not None, 'Unknown final arms in '+folder.name)
        candidates[(kind, tuple(cfg['tasks']))].append((folder,cfg))
    require(len(candidates) == len(schedule), 'Unexpected or missing final task batches')
    selected=[]; rows=[]; failures=[]; batch_rows=[]
    for batch in schedule:
        key=(batch['kind'],tuple(batch['tasks']))
        found=candidates.get(key,[])
        require(len(found)==1, 'Missing/duplicate final attempts for '+str(key)+'; do not pick best')
        folder,cfg=found[0]
        require(cfg['source_sha256']==source, 'Agent source hashes differ: '+folder.name)
        require(cfg['package_versions']==package_versions, 'Package versions differ: '+folder.name)
        require(cfg['model']==plan['model'] and cfg['max_steps']==batch['max_steps'], 'Model/budget differs')
        require(cfg['completion_metric']==plan['completion_metric'], 'Metric differs')
        require(cfg['planned_api_call_ceiling']==batch['api_call_ceiling'], 'Batch cap differs')
        pairs=read(folder/'pairs.json'); summary=read(folder/'summary.json')
        require(len(pairs)==3 and summary['interrupted'] is False, 'Incomplete/interrupted batch')
        arms=cfg['arms']
        require(cfg['arm_order']==f'alternates by pair; starts {arms[0]}','Order configuration differs')
        if batch['kind']=='recovery':
            require(cfg['controlled_failure_scenario']=='disabled_textbox_timeout','Wrong fault')
            require(cfg['max_recoveries']=={'recovery_off':0,'recovery_on':1},'Wrong recoveries')
        else: require(cfg['max_recoveries']==0,'Planning recovery enabled')
        for i,(pair,seed) in enumerate(zip(pairs,batch['seeds']),1):
            require(pair['task']==batch['tasks'][0] and pair['seed']==seed and pair['matched'] is True,'Pair coverage differs')
            require(set(pair['arms'])==set(arms),'Missing/extra arm')
            records=[pair['arms'][a] for a in arms]
            require(records[0]['initial_observation_sha256']==records[1]['initial_observation_sha256'] and records[0]['initial_observation_sha256'],'Initial hashes differ')
            if batch['kind']=='recovery': require(matching_failures(*records),'Failure signatures differ')
            for arm in arms:
                r=pair['arms'][arm]
                require(read(folder/f'{i:02d}-{pair["task"]}-seed{seed}-{arm}.json')==r,'Episode/pairs file differs')
                require(r['arm']==arm and r['task']==pair['task'] and r['seed']==seed,'Episode identity differs')
                require(r['max_steps']==batch['max_steps'] and r['completion_metric']==plan['completion_metric'] and r['model']==plan['model'],'Episode config differs')
                require(type(r['success']) is bool and type(r['api_usage_may_be_incomplete']) is bool,'Invalid flags')
                require(0<=r['steps']<=batch['max_steps'] and 0<=r['api_calls']<=(1 if arm=='oneshot' else batch['max_steps']),'Episode budget exceeded')
                if r['success']: require(r['reason']=='benchmark_success' and abs(r['reward']-1)<=1e-9,'Inconsistent success')
                row={'batch':batch['batch_id'],'kind':batch['kind'],'folder':folder.name,**r}
                rows.append(row)
                if not r['success'] and batch['kind']=='planning':failures.append(row)
        recalculated=(summarize_pairs(pairs,3,batch['max_steps']) if batch['kind']=='planning' else summarize(pairs,3,batch['max_steps'],'disabled_textbox_timeout'))
        require(summary=={**recalculated,'interrupted':False},'Recomputed summary differs: '+folder.name)
        batch_rows.append({'batch':batch['batch_id'],'folder':folder.name,'kind':batch['kind'],'task':batch['tasks'][0],'api_calls':summary['reported_api_calls'],'matched_pairs':3})
        selected.append(folder)
    totals={}
    for arm in ['oneshot','iterative','recovery_off','recovery_on']:
        rr=[r for r in rows if r['arm']==arm]
        totals[arm]={'episodes':len(rr),'successes':sum(r['success'] for r in rr),'success_rate':sum(r['success'] for r in rr)/len(rr),'failure_reasons':dict(Counter(r['reason'] for r in rr if not r['success'])),'potentially_incomplete_usage_episodes':sum(r['api_usage_may_be_incomplete'] for r in rr)}
        for k in ['api_calls','steps','duration_seconds','input_tokens','output_tokens']:
            totals[arm]['total_'+k]=sum(r[k] for r in rr)
            totals[arm]['mean_'+k]=sum(r[k] for r in rr)/len(rr)
    task_rows=[]
    for t in plan['tasks']:
        if t['selection']!='primary':continue
        task_rows.append({'task':t['task'],'family':t['family'],**{a:sum(r['success'] for r in rows if r['kind']=='planning' and r['task']==t['task'] and r['arm']==a) for a in ['oneshot','iterative']}})
    family_rows=[]
    for family in sorted({t['family'] for t in task_rows}):
        tt=[t for t in task_rows if t['family']==family]
        family_rows.append({'family':family,'task_ids':len(tt),'episodes_per_arm':3*len(tt),**{a:sum(t[a] for t in tt) for a in ['oneshot','iterative']}})
    audit={'audit_status':'passed','protocol_version':'1.0','frozen_agent_commit':plan['agent_commit'],'batches':batch_rows,'scheduled_pairs':66,'matched_pairs':66,'episodes':len(rows),'totals':totals,'planning_tasks':task_rows,'families':family_rows,'planning_failure_count':len(failures),'reported_api_calls':sum(r['api_calls'] for r in rows),'reported_input_tokens':sum(r['input_tokens'] for r in rows),'reported_output_tokens':sum(r['output_tokens'] for r in rows),'potentially_incomplete_usage_episodes':sum(r['api_usage_may_be_incomplete'] for r in rows),'limits':['Episode exports omit action histories, goals, per-step observations, terminal/truncated flags and raw model responses. Exact action-level root causes and terminal flags cannot be independently reconstructed.','Arm order is verified as configured, not independently timestamped execution order.','Current frozen sources/versions match; run config records agent source/package versions but not all supporting-asset hashes at run time.']}
    output.mkdir(parents=True)
    evidence=output/'docs/evidence/final-v1';evidence.mkdir(parents=True)
    provenance={}
    for batch,folder in zip(schedule,selected):
        dest=evidence/batch['batch_id'];dest.mkdir()
        for p in sorted(folder.glob('*.json')):
            shutil.copyfile(p,dest/p.name)
            provenance[str((dest/p.name).relative_to(output))]={'source':str(p),'sha256':sha(p)}
    for filename,data in [('audit-summary.json',audit),('planning-failures.json',failures),('episode-metrics.json',rows),('provenance.json',provenance)]:
        (evidence/filename).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({'audit_status':'passed','episodes':len(rows),'batches':len(selected),'reported_api_calls':audit['reported_api_calls'],'totals':totals},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.root.resolve(),a.output.resolve())
