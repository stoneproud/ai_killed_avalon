"""Trusted operator setup/export CLI. Player code runs only in its seat sandbox."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import uuid
from host import Host, atomic, encoded, locked

HERE = Path(__file__).resolve().parent
VENDOR = HERE / 'vendor'


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, capture_output=True, **kwargs).stdout


def dependencies():
    # Git for Windows bundles these command-line tools. No account paths/config copied.
    if os.name == 'nt':
        bundled = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Git/usr/bin'
        if bundled.exists():
            os.environ['PATH'] = str(bundled) + os.pathsep + os.environ['PATH']
    missing = [x for x in ('git', 'perl', 'openssl', 'ssh-keygen') if not shutil.which(x)]
    if missing:
        raise RuntimeError('Missing executables: ' + ', '.join(missing))


def verify_vendor():
    manifest = json.loads((VENDOR / 'provenance.json').read_text('utf-8'))
    for item in manifest['files']:
        if hashlib.sha256((VENDOR / item['path']).read_bytes()).hexdigest() != item['sha256']:
            raise RuntimeError('Changed original player material: ' + item['path'])
    return manifest


def initialize(root):
    dependencies()
    verify_vendor()
    document = VENDOR / 'artifacts/p4_protocol_v1.md'
    h = Host.init(root, hashlib.sha256(document.read_bytes()).hexdigest())
    pubkeys = {}
    records = []
    # No role deal or old player history. Setup failure remains an incomplete room.
    for seat in range(1, 9):
        work = root / 'players' / f'p{seat}'
        (work / 'access').mkdir(mode=0o700)
        (work / 'private').mkdir(mode=0o700)
        key = work / 'access/id_bus'
        run(['ssh-keygen', '-q', '-t', 'rsa', '-b', '3072', '-m', 'PEM',
             '-N', '', '-C', f'fresh-challenge-p{seat}', '-f', key])
        key.chmod(0o600)
        ssh_public = key.with_suffix('.pub').read_bytes()
        pem = run(['openssl', 'pkey', '-in', key, '-pubout'])
        pubkeys[seat] = pem
        records.append(dict(seat=seat, ssh_sha256=hashlib.sha256(ssh_public).hexdigest(),
                            pem_sha256=hashlib.sha256(pem).hexdigest()))
        atomic(work / 'seat.json', dict(seat=seat, protocol=h.s['protocol'],
                                      origin='fresh scenario assumption, not original player memory'))
        shutil.copytree(VENDOR, work / 'reference')
    files = {}
    for seat in range(1, 9):
        work = root / 'players' / f'p{seat}'
        (work / 'registered_pem').mkdir()
        for sender, pem in pubkeys.items():
            (work / 'registered_pem' / f'p{sender}.pem').write_bytes(pem)
        files[f'public/access/p{seat}.pub'] = (work / 'access/id_bus.pub').read_bytes()
        files[f'public/registered_pem/p{seat}.pem'] = pubkeys[seat]
    registration = dict(schema='fresh-challenge-registration-v1', protocol=h.s['protocol'],
        protocol_document_sha256=h.s['protocol_sha256'], registered_public_keys=records,
        binding='Original document/tools unchanged. Original historical key hashes are replaced only by this fresh run registration.',
        adopted_by_scenario=list(range(1, 9)), roles_generated=False)
    files['public/challenge_registration.json'] = encoded(registration)
    h.publish(files)
    atomic(root / 'setup_complete.json', dict(snapshot=h.s['snapshot'], registration=registration))
    return h.status()


def export_seat(root, seat):
    """Only main-reachable objects, no local hardlinks or other refs/unreachable objects."""
    if not (root / 'setup_complete.json').exists():
        raise RuntimeError('Room setup is incomplete')
    with locked(root):
        h = Host(root)
        request = h.step(seat)
        export = root / 'exports' / f'p{seat}' / uuid.uuid4().hex
        export.mkdir(parents=True)
        repo = export / 'public_repo'
        run(['git', 'clone', '--no-local', '--single-branch', '--branch', 'main',
             '--no-checkout', h.repo, repo])
        actual = run(['git', '-C', repo, 'rev-parse', 'HEAD']).decode().strip()
        if actual != request['seen_snapshot']:
            raise RuntimeError('Snapshot changed while exporting')
        # Remove host filesystem location from player-readable configuration.
        run(['git', '-C', repo, 'remote', 'remove', 'origin'])
        atomic(export / 'request.json', request)
        atomic(export / 'export_manifest.json', dict(seat=seat, snapshot=actual,
            source='main-reachable Git objects only', private_view='this seat only'))
    return export


def read_reply(path):
    path = path.absolute()
    for parent in (path, *path.parents):
        info = parent.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Reply path must not traverse symlinks/junctions')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 8*1024*1024:
        raise ValueError('Reply must be a regular bounded JSON file')
    with path.open('rb') as stream:
        data = stream.read(8*1024*1024+1)
    if len(data) > 8*1024*1024:
        raise ValueError('Reply grew beyond size limit')
    return json.loads(data)


def sandbox_args(work, export, engine=None):
    """Shared restrictive launch policy, also used by the real-container probe."""
    engine = engine or shutil.which('podman') or shutil.which('docker')
    if not engine:
        raise RuntimeError('Install Podman or Docker to run isolated players')
    return [engine, 'run', '--rm', '--network=none', '--read-only', '--cap-drop=ALL',
        '--security-opt=no-new-privileges', '--pids-limit=128', '--memory=1g',
        '--tmpfs=/tmp:rw,noexec,nosuid,size=128m',
        '--mount', f'type=bind,src={work},dst=/workspace',
        '--mount', f'type=bind,src={export},dst=/input,ro=true',
        '--workdir=/workspace']


def sandbox(root, seat, shell=False):
    export = export_seat(root, seat)
    work = root / 'players' / f'p{seat}'
    args = sandbox_args(work, export)
    if shell:
        args += ['-it']
    args += ['sealed-mail-challenge:local']
    if shell:
        args += ['bash']
    else:
        output = 'reply-' + uuid.uuid4().hex + '.json'
        args += ['python', '/opt/challenge/bot.py', '--workspace', '/workspace',
                 '--request', '/input/request.json', '--public-repo', '/input/public_repo',
                 '--output', '/workspace/' + output]
    subprocess.run(args, check=True)
    return {'seat':seat, 'export':str(export),
            'reply':None if shell else str(work / output), 'submitted':False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    sub = p.add_subparsers(dest='cmd', required=True)
    for cmd in ('init', 'status', 'deal', 'doctor'):
        sub.add_parser(cmd)
    for cmd in ('export', 'sandbox', 'shell', 'submit'):
        s = sub.add_parser(cmd); s.add_argument('--seat', type=int, choices=range(1,9), required=True)
        if cmd == 'submit': s.add_argument('--file', type=Path, required=True)
    args = p.parse_args(); root = args.root.resolve()
    if args.cmd == 'doctor':
        dependencies(); verify_vendor()
        result = dict(tools={x:shutil.which(x) for x in ('git','perl','openssl','ssh-keygen')},
                      vendor_verified=True, model_calls=0)
    elif args.cmd == 'init': result = initialize(root)
    elif args.cmd == 'export': result = dict(export=str(export_seat(root,args.seat)))
    elif args.cmd in ('sandbox','shell'): result = sandbox(root,args.seat,args.cmd=='shell')
    else:
        if not (root / 'setup_complete.json').exists(): raise RuntimeError('Setup incomplete')
        with locked(root):
            h = Host(root)
            if args.cmd == 'status': result = h.status()
            elif args.cmd == 'deal': result = h.deal()
            else:
                # Do not execute player output or follow it as an instruction.
                result = h.submit(args.seat,read_reply(args.file))
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
