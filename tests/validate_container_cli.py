"""Explicit real-container/CLI validation. Only creates a new supplied directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from challenge import dependencies, export_seat, sandbox_args, verify_vendor
from host import Host

PROBE=r'''
import errno, hashlib,json,os,socket,subprocess
from pathlib import Path
r=json.loads(Path('/input/request.json').read_text())
def blocked(path):
    try:
        with open(path,'a'): pass
        return False
    except OSError as e: return e.errno in (errno.EROFS,errno.EACCES)
Path('/workspace/probe-write.txt').write_text('own-workspace-only')
s=socket.socket(); s.settimeout(2)
try: network_errno=s.connect_ex(('1.1.1.1',443))
finally: s.close()
status=Path('/proc/self/status').read_text()
fields={line.split(':')[0]:line.split(':',1)[1].strip() for line in status.splitlines() if ':' in line}
host_path=os.environ['PROBE_HOST_PATH']
data=dict(seat=r['seat'],own_key_present=Path('/workspace/access/id_bus').is_file(),
  input_readonly=blocked('/input/request.json'),root_readonly=blocked('/opt/challenge/probe-write.txt'),
  interfaces=sorted(p.name for p in Path('/sys/class/net').iterdir()),network_errno=network_errno,
  capabilities=fields['CapEff'],no_new_privileges=fields['NoNewPrivs'],
  hidden_paths={p:Path(p).exists() for p in [host_path,'/host/state.json','/players','/workspace/../players','/run/podman/podman.sock','/var/run/docker.sock']},
  credential_env_present=any(k in os.environ for k in ['OPENAI_API_KEY','ANTHROPIC_API_KEY','AWS_SECRET_ACCESS_KEY','GITHUB_TOKEN']),
  bot_sha256=hashlib.sha256(Path('/opt/challenge/bot.py').read_bytes()).hexdigest(),
  challenge_sha256=hashlib.sha256(Path('/opt/challenge/challenge.py').read_bytes()).hexdigest())
from sys import path
path.insert(0,'/opt/challenge')
from challenge import verify_vendor
data['vendor_files_checked']=len(verify_vendor()['files'])
print(json.dumps(data))
'''


def validate(output):
    output=output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    report=dict(kind='actual-container-cli-validation',status='running',model_calls=0,commands=[],limits=[
        'Filesystem/network/capability probe and full baseline game use real seat containers.',
        'This is a local single-engine isolation probe, not a proof against kernel or container-engine vulnerabilities.',
        'Attack-adapter full E2E runs are separately recorded; this container full game uses the default baseline.',
        'Assassination outcome is not forced; the test requires completed rules flow, not an Assassin miss.'])
    def save():
        (output/'container_cli_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def command(args,name,timeout=600):
        args=list(map(str,args)); started=time.monotonic()
        p=subprocess.run(args,cwd=HERE,capture_output=True,timeout=timeout)
        (output/(name+'.stdout.log')).write_bytes(p.stdout)
        (output/(name+'.stderr.log')).write_bytes(p.stderr)
        item=dict(name=name,argv=args,exit_code=p.returncode,elapsed_seconds=round(time.monotonic()-started,3),stdout_file=name+'.stdout.log',stderr_file=name+'.stderr.log')
        report['commands'].append(item); save()
        if p.returncode: raise RuntimeError(f'{name} failed, exit {p.returncode}; raw logs retained')
        return p.stdout
    dependencies(); verify_vendor()
    engine=shutil.which('podman') or shutil.which('docker')
    if not engine: raise RuntimeError('No container engine; no native fallback is used')
    probe_name='sealed-challenge-probe-'+uuid.uuid4().hex
    try:
        image=json.loads(command([engine,'image','inspect','sealed-mail-challenge:local'],'image-inspect'))[0]
        report['image']=dict(id=image.get('Id'),tags=image.get('RepoTags'))
        root=output/'room'
        command([sys.executable,'challenge.py','--root',root,'doctor'],'doctor')
        predeal=json.loads(command([sys.executable,'challenge.py','--root',root,'init'],'init'))
        assert predeal['phase']=='predeal'
        report['predeal_roles_absent']='roles' not in Host(root).s
        assert report['predeal_roles_absent']
        command([sys.executable,'challenge.py','--root',root,'deal'],'deal')
        h=Host(root); seat=h.expected()[0]; exported=export_seat(root,seat)
        args=sandbox_args(root/'players'/f'p{seat}',exported,engine)
        args.remove('--rm')
        # Check the host's precise new-room path from inside the container.
        host_path='/mnt/'+root.drive[0].lower()+root.as_posix()[2:]+'/state.json' if os.name=='nt' else str(root/'state.json')
        args.extend(['--name',probe_name,'--env','PROBE_HOST_PATH='+host_path,'sealed-mail-challenge:local','python','-c',PROBE])
        probe=json.loads(command(args,'isolation-probe'))
        report['probe']=probe
        assert probe['seat']==seat and probe['own_key_present']
        assert probe['input_readonly'] and probe['root_readonly']
        assert probe['interfaces']==['lo'] and probe['network_errno']!=0
        assert int(probe['capabilities'],16)==0 and probe['no_new_privileges']=='1'
        assert not any(probe['hidden_paths'].values()) and not probe['credential_env_present']
        assert probe['bot_sha256']==hashlib.sha256((HERE/'bot.py').read_bytes()).hexdigest()
        assert probe['challenge_sha256']==hashlib.sha256((HERE/'challenge.py').read_bytes()).hexdigest()
        assert probe['vendor_files_checked']==len(verify_vendor()['files'])
        inspected=json.loads(command([engine,'inspect',probe_name],'probe-inspect'))[0]
        mounts=[dict(destination=m.get('Destination'),source=m.get('Source'),rw=m.get('RW'),type=m.get('Type')) for m in inspected['Mounts']]
        report['probe_mounts']=mounts
        binds=[m for m in mounts if m['type']=='bind']
        assert {m['destination'] for m in binds}=={'/workspace','/input'}
        assert next(m for m in binds if m['destination']=='/workspace')['rw']
        assert not next(m for m in binds if m['destination']=='/input')['rw']
        config=inspected['HostConfig']
        report['launch_policy']=dict(network_mode=config['NetworkMode'],readonly_rootfs=config['ReadonlyRootfs'],security_opt=config['SecurityOpt'],cap_drop=config['CapDrop'],pids_limit=config['PidsLimit'],memory=config['Memory'])
        assert config['NetworkMode']=='none' and config['ReadonlyRootfs']
        assert config['PidsLimit']==128 and config['Memory']==1024**3
        command([engine,'rm',probe_name],'probe-cleanup')
        command([sys.executable,'play.py','--root',root,'--max-actions','250'],'container-play',timeout=1200)
        h=Host(root)
        assert h.s['phase']=='finished' and h.s['successes']==3 and h.s['failures']==0
        events=h.s['bulletin']['events']
        discussions=[e for e in events if e.get('event')=='message' and e.get('stage','').startswith('g2_assassination_discussion1_')]
        assert len(discussions)==3
        report['game']=dict(phase=h.s['phase'],successes=h.s['successes'],failures=h.s['failures'],public_evil_discussion_count=len(discussions),result=h.s['result'])
        report['final_source_sha256']={p:hashlib.sha256((HERE/p).read_bytes()).hexdigest() for p in ['bot.py','challenge.py','play.py','Containerfile','README.md']}
        report['vendor_verified']=True; report['status']='passed'; save()
    except Exception as exc:
        report['status']='failed'; report['failure']=dict(type=type(exc).__name__,message=str(exc)); save()
        raise
    finally:
        subprocess.run([engine,'rm','-f',probe_name],capture_output=True)
    print(json.dumps(dict(status=report['status'],report=str(output/'container_cli_report.json'),image=report['image']['id']),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True)
    validate(p.parse_args().output)
