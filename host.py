"""Fresh adopted-protocol Avalon room. Standard library only; Git is external.

Trusted operator CLI, not an authenticated remote service. Never expose RUN to
players: it contains host-only role assignments and pending secret actions.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile

SEATS = list(range(1, 9))
SIZES = [3, 4, 4, 5, 5]
PROTOCOL = 'sealed-mail-2r-v1'


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def attachment_path(path):
    if not isinstance(path, str) or len(path) > 240 or not re.fullmatch(r'artifacts/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.json', path):
        raise ValueError('Unsafe attachment path')
    reserved = {'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(1,10)), *(f'lpt{i}' for i in range(1,10))}
    for part in path.split('/'):
        if part in ('.', '..') or part.lower() == '.git' or part.endswith(('.', ' ')) or part.split('.')[0].lower() in reserved:
            raise ValueError('Unsafe attachment path')
    return path


def atomic(path, value):
    temporary = path.with_suffix('.tmp')
    with open(temporary, 'wb') as f:
        f.write(encoded(value))
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, path)


@contextlib.contextmanager
def locked(root):
    with open(root / 'host.lock', 'a+b') as f:
        f.seek(0)
        if os.name == 'nt':
            import msvcrt
            if f.read(1) == b'':
                f.write(b'0'); f.flush()
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == 'nt':
                f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class Host:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.repo = self.root / 'public_repo'
        pending = self.root / 'pending.json'
        if pending.exists():
            state = json.loads(pending.read_bytes())
            self.git('update-ref', 'refs/heads/main', state['snapshot'])
            atomic(self.root / 'state.json', state)
            pending.unlink()
        self.s = json.loads((self.root / 'state.json').read_bytes())
        if self.s.get('schema') != 'challenge-sealed-mail-host-v1':
            raise ValueError('Unsupported room schema')

    def git(self, *args, data=None, env=None):
        return subprocess.run(['git', '--git-dir=' + str(self.repo), *args], input=data,
                              env=env, check=True, capture_output=True).stdout.decode().strip()

    @classmethod
    def init(cls, root, protocol_sha256=None):
        root = Path(root).resolve()
        if root.exists():
            raise ValueError('init requires a nonexistent run directory')
        if protocol_sha256 is not None and (not isinstance(protocol_sha256, str) or len(protocol_sha256) != 64 or
                any(c not in '0123456789abcdef' for c in protocol_sha256)):
            raise ValueError('protocol SHA256 must be 64 lowercase hexadecimal digits')
        root.mkdir(parents=True, mode=0o700)
        (root / 'private').mkdir(mode=0o700)
        for n in SEATS:
            (root / 'players' / f'p{n}').mkdir(parents=True, mode=0o700)
        repo = root / 'public_repo'
        subprocess.run(['git', 'init', '--bare', '--object-format=sha1', str(repo)], check=True, capture_output=True)
        obj = cls.__new__(cls); obj.root = root; obj.repo = repo
        obj.git('config', 'user.name', 'Challenge Host')
        obj.git('config', 'user.email', 'host@challenge.invalid')
        obj.s = dict(schema='challenge-sealed-mail-host-v1', protocol=PROTOCOL,
                     protocol_sha256=protocol_sha256, adopted=SEATS, game_id='g2',
                     origin='fresh challenge; not a replay of an earlier g1',
                     phase='predeal', quest=1, attempt=1, rejections=0,
                     successes=0, failures=0, pending={}, bulletin={'events': [], 'files': []})
        obj.publish({'README.md': b'Fresh adopted-protocol challenge. No earlier game was played.\n'})
        for n in SEATS:
            obj.git('update-ref', f'refs/heads/p{n}', obj.s['snapshot'])
        obj.git('symbolic-ref', 'HEAD', 'refs/heads/main')
        return obj

    def commit(self, files, parent, label):
        with tempfile.TemporaryDirectory(dir=self.root) as d:
            env = dict(os.environ, GIT_INDEX_FILE=str(Path(d) / 'index'))
            if parent:
                self.git('read-tree', parent, env=env)
            else:
                self.git('read-tree', '--empty', env=env)
            for path, data in files.items():
                blob = self.git('hash-object', '-w', '--stdin', data=data)
                self.git('update-index', '--add', '--cacheinfo', f'100644,{blob},{path}', env=env)
            tree = self.git('write-tree', env=env)
            args = ['commit-tree', tree]
            if parent:
                args += ['-p', parent]
            return self.git(*args, data=(label + '\n').encode())

    def publish(self, files=None):
        files = dict(files or {})
        files['public/bulletin.json'] = encoded(self.s['bulletin'])
        snapshot = self.commit(files, self.s.get('snapshot'), 'public host publication')
        self.s['snapshot'] = snapshot
        # Recovery journal is durable before the visible main ref moves.
        atomic(self.root / 'pending.json', self.s)
        self.git('update-ref', 'refs/heads/main', snapshot)
        atomic(self.root / 'state.json', self.s)
        (self.root / 'pending.json').unlink()

    def save(self):
        atomic(self.root / 'state.json', self.s)

    def event(self, kind, **fields):
        b = self.s['bulletin']
        b['events'].append(dict(event_id=f'e{len(b["events"])+1}', event=kind,
                                game_id='g2', **fields))

    def deal(self):
        if self.s['phase'] != 'predeal':
            raise ValueError('Room already dealt')
        seats = SEATS[:]; secrets.SystemRandom().shuffle(seats)
        roles = ['merlin', 'percival', 'servant', 'servant', 'servant', 'morgana', 'assassin', 'minion']
        self.s['roles'] = {str(n): role for n, role in zip(seats, roles)}
        self.s['leader'] = secrets.choice(SEATS)
        self.s['phase'] = 'order'
        self.event('game_start', initial_leader=self.s['leader'], quest_sizes=SIZES,
                   fourth_quest_fail_threshold=2, protocol=PROTOCOL)
        self.publish()
        return self.status()

    def view(self, seat):
        role = self.s['roles'][str(seat)]
        bad = sorted(n for n in SEATS if self.s['roles'][str(n)] in ('morgana', 'assassin', 'minion'))
        view = dict(role=role, faction='evil' if seat in bad else 'good')
        if role == 'merlin' or seat in bad:
            view['evil_seats'] = bad
        if role == 'percival':
            view['merlin_or_morgana'] = sorted(n for n in SEATS if self.s['roles'][str(n)] in ('merlin', 'morgana'))
        return view

    def stage(self):
        s = self.s; q = s['quest']; a = s['attempt']
        return {'order': f'g2_q{q}_order{a}',
                'speech': f'g2_q{q}_proposal{a}_speech_s{s.get("speech_index",0)+1}_p{self.expected()[0] if s["phase"]=="speech" else 0}',
                'vote': f'g2_q{q}_vote{a}', 'task': f'g2_q{q}_task',
                'assassination_speech': f'g2_assassination_discussion1_s{s.get("speech_index",0)+1}_p{self.expected()[0] if s["phase"]=="assassination_speech" else 0}',
                'assassination': 'g2_assassination', 'predeal': 'predeal', 'finished': 'finished'}[s['phase']]

    def expected(self):
        s = self.s
        if s['phase'] == 'order': return [s['leader']]
        if s['phase'] in ('speech', 'assassination_speech'): return [s['order'][s['speech_index']]]
        if s['phase'] == 'vote': return SEATS[:]
        if s['phase'] == 'task': return s['team'][:]
        if s['phase'] == 'assassination': return [n for n in SEATS if s['roles'][str(n)] == 'assassin']
        return []

    def status(self):
        # No pending seat list or partial ballots: submission timing is private.
        keys = ['schema', 'protocol', 'protocol_sha256', 'origin', 'game_id', 'phase',
                'snapshot', 'quest', 'attempt', 'leader', 'successes', 'failures',
                'rejections', 'team', 'result']
        result = {k: self.s[k] for k in keys if k in self.s}
        hidden = self.s['phase'] in ('assassination_speech', 'assassination')
        result['stage'] = 'g2_assassination_discussion1' if self.s['phase']=='assassination_speech' else self.stage()
        if not hidden:
            result['eligible_seats'] = self.expected()
        return result

    def step(self, seat):
        if type(seat) is not int or seat not in SEATS: raise ValueError('Invalid seat')
        result = self.status()
        result.update(seat=seat, seen_snapshot=self.s['snapshot'],
                      submitted=str(seat) in self.s['pending'],
                      eligible=seat in self.expected(), public_bulletin_path='public/bulletin.json')
        if result['eligible']:
            result['stage'] = self.stage()
        if 'roles' in self.s: result['private_view'] = self.view(seat)
        result['action_schema'] = {'order': {'direction': 'clockwise|counterclockwise'},
            'speech': {'team': 'leader only: distinct seat list of required size; others {}'},
            'vote': {'approve': 'boolean'}, 'task': {'card': 'success|fail'},
            'assassination_speech': {}, 'assassination': {'target': 'good seat'},
            'predeal': {}, 'finished': {}}[self.s['phase']]
        return result

    def finish(self, winner, reason, **extra):
        self.s['phase'] = 'finished'
        self.s['result'] = dict(winner=winner, reason=reason, **extra)
        self.event('game_over', **self.s['result'])

    def submit(self, seat, value):
        s = self.s; phase = s['phase']
        if type(seat) is not int or seat not in self.expected(): raise ValueError('Seat is not eligible')
        if str(seat) in s['pending']: raise ValueError('Action already submitted')
        if not isinstance(value, dict) or value.get('seen_snapshot') != s['snapshot']:
            raise ValueError('Exact seen_snapshot required')
        try:
            if len(encoded(value)) > 8 * 1048576:
                raise ValueError('Submission exceeds 8MiB')
        except (TypeError, RecursionError) as exc:
            raise ValueError('Submission must be a bounded JSON object') from exc
        action = value.get('action')
        if not isinstance(action, dict): raise ValueError('action object required')
        public = phase in ('speech', 'assassination_speech')
        if not public and any(k in value for k in ('message', 'attachments')):
            raise ValueError('Secret/control phase cannot publish attachments or messages')
        if phase == 'order':
            if set(action) != {'direction'} or action['direction'] not in ('clockwise', 'counterclockwise'):
                raise ValueError('Invalid direction')
        elif phase == 'speech':
            if seat == s['leader']:
                team = action.get('team')
                if set(action) != {'team'} or not isinstance(team, list) or len(team) != SIZES[s['quest']-1] or any(type(n) is not int or n not in SEATS for n in team) or len(set(team)) != len(team):
                    raise ValueError('Invalid team')
            elif action: raise ValueError('Only leader proposes a team')
        elif phase == 'vote':
            if set(action) != {'approve'} or type(action['approve']) is not bool: raise ValueError('Invalid vote')
        elif phase == 'task':
            if set(action) != {'card'} or action['card'] not in ('success','fail') or (self.view(seat)['faction']=='good' and action['card']!='success'): raise ValueError('Illegal task card')
        elif phase == 'assassination':
            target = action.get('target')
            if set(action) != {'target'} or type(target) is not int or target not in SEATS or self.view(target)['faction'] != 'good': raise ValueError('Invalid assassination target')
        elif action: raise ValueError('No action fields allowed')
        files = {}
        if public:
            message = value.get('message')
            if not isinstance(message, dict) or type(message.get('seat')) is not int or message.get('seat') != seat or message.get('stage') != self.stage() or message.get('game_id') != 'g2':
                raise ValueError('Public message must identify exact seat/stage/game_id')
            if len(encoded(message)) > 65536:
                raise ValueError('Public message exceeds 64KiB')
            attachments = value.get('attachments', [])
            if not isinstance(attachments, list) or len(attachments) > 32: raise ValueError('Invalid attachments')
            paths_by_case = {f['source_path'].casefold(): f['source_path']
                             for f in s['bulletin']['files'] if f['from'] == seat}
            for item in attachments:
                if not isinstance(item, dict) or set(item) != {'path','content'}: raise ValueError('Attachment path/content required')
                path = attachment_path(item['path'])
                if path in files: raise ValueError('Duplicate attachment path')
                if path.casefold() in paths_by_case and paths_by_case[path.casefold()] != path:
                    raise ValueError('Case-colliding attachment path')
                paths_by_case[path.casefold()] = path
                content = encoded(item['content'])
                if len(content)>1048576: raise ValueError('Attachment exceeds 1MiB')
                files[path] = content
            stage = self.stage()
            files[f'messages/{stage}.json'] = encoded(message)
            source = self.commit(files, s['snapshot'], f'seat {seat} {stage}')
            self.git('update-ref', f'refs/heads/p{seat}', source)
            self.event('message', stage=stage, by=seat, branch_commit=source, message=message)
            published = {}
            for path, data in files.items():
                dest = f'public/files/p{seat}/{path}'
                published[dest] = data
                if path.startswith('artifacts/'):
                    s['bulletin']['files'].append(dict(path=dest, source_path=path,
                        source_commit=source, **{'from':seat}, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)))
            s['speech_index'] += 1
            if s['speech_index'] == len(s['order']):
                if phase == 'speech':
                    s['team'] = action['team']; s['phase'] = 'vote'
                    self.event('team_proposed', quest=s['quest'], leader=s['leader'], team=s['team'], stage=f'g2_q{s["quest"]}_proposal{s["attempt"]}')
                else: s['phase'] = 'assassination'
            self.publish(published)
        elif phase == 'order':
            direction = 1 if action['direction']=='clockwise' else -1
            leader=s['leader']; s['order']=[(leader-1+direction*i)%8+1 for i in range(1,9)]
            s['speech_index']=0; s['phase']='speech'
            self.event('speaking_order', order=s['order'], direction=action['direction'], quest=s['quest'], attempt=s['attempt'])
            self.publish()
        elif phase in ('vote','task'):
            s['pending'][str(seat)]=action
            if len(s['pending']) < len(self.expected()): self.save()
            else:
                if phase=='vote':
                    votes={n:v['approve'] for n,v in s['pending'].items()}; approved=sum(votes.values())>=5
                    self.event('team_vote', quest=s['quest'], team=s['team'], votes=votes, approved=approved, stage=self.stage())
                    s['leader']=s['leader']%8+1
                    if approved: s['phase']='task'; s['rejections']=0
                    else:
                        s['rejections']+=1; s['attempt']+=1; s['phase']='order'
                        if s['rejections']==5: self.finish('evil','five_consecutive_rejected_teams')
                else:
                    fails=sum(v['card']=='fail' for v in s['pending'].values()); passed=fails<(2 if s['quest']==4 else 1)
                    s['successes']+=int(passed); s['failures']+=int(not passed)
                    self.event('quest_result', quest=s['quest'], team=s['team'], fails=fails, passed=passed, successes=s['successes'], failures=s['failures'])
                    if s['failures']==3: self.finish('evil','three_failed_quests')
                    elif s['successes']==3:
                        s['phase']='assassination_speech'; s['speech_index']=0
                        s['order']=sorted(n for n in SEATS if self.view(n)['faction']=='evil')
                        self.event('assassination_phase')
                    else: s['quest']+=1; s['attempt']=1; s['phase']='order'
                s['pending']={}; self.publish()
        else:
            target=action['target']; hit=self.view(target)['role']=='merlin'
            self.finish('evil' if hit else 'good','assassin_hit_merlin' if hit else 'assassin_missed_merlin', assassin=seat, target=target, hit_merlin=hit)
            self.publish()
        return {'accepted':True,'seat':seat,'stage':self.status()['stage'],'snapshot':s['snapshot']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', required=True, type=Path)
    subs=p.add_subparsers(dest='command',required=True)
    init=subs.add_parser('init'); init.add_argument('--protocol-sha256')
    for cmd in ('status','deal'): subs.add_parser(cmd)
    step=subs.add_parser('step'); step.add_argument('--seat',type=int,required=True)
    submit=subs.add_parser('submit'); submit.add_argument('--seat',type=int,required=True); submit.add_argument('--file',type=Path,required=True)
    a=p.parse_args()
    try:
        if a.command=='init': result=Host.init(a.root,a.protocol_sha256).status()
        else:
            with locked(a.root):
                h=Host(a.root)
                if a.command=='status': result=h.status()
                elif a.command=='deal': result=h.deal()
                elif a.command=='step': result=h.step(a.seat)
                else:
                    if a.file.stat().st_size > 8 * 1048576:
                        raise ValueError('Submission exceeds 8MiB')
                    result=h.submit(a.seat,json.loads(a.file.read_bytes()))
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError, RecursionError, OSError, subprocess.CalledProcessError) as e:
        p.exit(2, 'host: '+str(e)+'\n')


if __name__=='__main__': main()
