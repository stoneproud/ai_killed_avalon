"""Seat-local adapter for the byte-preserved sealed-mail tools; no model calls."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import uuid

TOOLS = Path(__file__).resolve().parent / 'vendor/tools/sealed_v1'
BROADCAST = '按密封信两圈冻结版v1提交本阶段材料，并按公共状态行动。'


class ProtocolError(RuntimeError):
    pass


class Bot:
    def __init__(self, workspace, request, public_repo, attack=None):
        self.work = Path(workspace)
        self.r = request if isinstance(request, dict) else json.loads(Path(request).read_text(encoding='utf-8'))
        self.repo = Path(public_repo)
        self.private = self.work / 'private'
        self.private.mkdir(parents=True, exist_ok=True)
        self.seat = self.r['seat']
        self.view = self.r['private_view']
        self.evil = self.view['faction'] == 'evil'
        ap = self.work / 'attack.json'
        self.attack = attack if attack is not None else (json.loads(ap.read_text()) if self.evil and ap.exists() else {})
        if self.attack and not self.evil:
            raise ProtocolError('Attack flags require an Evil seat')
        self.snapshot = self.r['seen_snapshot']
        self.pem = self.work / 'access/registered_pem'
        if not self.pem.exists():
            self.pem = self.work / 'registered_pem'
        self.bulletin = json.loads(self.blob(self.snapshot, 'public/bulletin.json'))
        registration = json.loads(self.blob(self.snapshot, 'public/challenge_registration.json'))
        for record in registration['registered_public_keys']:
            sender = record['seat']
            public = self.blob(self.snapshot, f'public/access/p{sender}.pub')
            pem = (self.pem / f'p{sender}.pem').read_bytes()
            if hashlib.sha256(public).hexdigest() != record['ssh_sha256'] or hashlib.sha256(pem).hexdigest() != record['pem_sha256']:
                raise ProtocolError('Registered key binding mismatch')

    def blob(self, snapshot, path):
        return subprocess.run(['git', '-C', str(self.repo), 'show', f'{snapshot}:{path}'], check=True, capture_output=True).stdout

    def fresh(self, value=None):
        p = self.private / (uuid.uuid4().hex + '.json')
        if value is not None:
            p.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return p

    def tool(self, name, *args):
        # Windows Perl expands brace/glob arguments before the script starts.
        # Send the exact argv through stdin so p5's literal {seat} survives.
        wrapper = 'use JSON::PP; my $a=decode_json(do{local $/;<STDIN>}); @ARGV=@$a; my $f=shift @ARGV; do $f; die $@ if $@;'
        argv = [str(TOOLS / (name + '.pl')), *map(str, args)]
        p = subprocess.run(['perl', '-e', wrapper], input=json.dumps(argv).encode(), capture_output=True)
        if p.returncode:
            raise ProtocolError(f'{name}: {p.stderr.decode(errors="replace").strip()}')
        return p.stdout

    def calc(self, tool, data, *args):
        return json.loads(self.tool(tool, self.fresh(data), *args))

    def reports(self, kind, quest=1, snapshot=None, own=None):
        snapshot = snapshot or self.snapshot
        attempt = 1 if kind in ('offer', 'x_source') else 2
        if own is not None:
            allowed = (kind in ('receipt', 'x_choice') and snapshot == self.snapshot
                       and self.r.get('phase') == 'speech'
                       and self.r.get('leader') == self.seat
                       and self.r.get('eligible') is True and self.r.get('submitted') is False
                       and self.r.get('quest') == quest and self.r.get('attempt') == 2
                       and (kind != 'receipt' or quest == 1)
                       and self.r.get('stage', '').startswith(f'g2_q{quest}_proposal2_speech_')
                       and self.r.get('stage', '').endswith(f'_p{self.seat}'))
            if not allowed:
                raise ProtocolError('Own report is allowed only for the eligible last leader speech in its current window')
        stem = f'g2_{kind}_' + (f'q{quest}_' if kind.startswith('x_') else '')
        template = 'artifacts/' + stem + 'p{seat}.json'
        bulletin = json.loads(self.blob(snapshot, 'public/bulletin.json'))
        index = json.loads(self.tool('p5_first_window_v1', 'g2', f'g2_q{quest}_proposal{attempt}_speech_', template, snapshot, self.fresh(bulletin)))
        if own is not None:
            slot = next(s for s in index['slots'] if s['seat'] == self.seat)
            if slot['status'] != 'no_first_event':
                raise ProtocolError('Cannot replace an occupied first slot, including an invalid first event')
        out = {}
        for slot in index['slots']:
            if slot['status'] != 'pinned_reference':
                continue
            raw = self.blob(snapshot, slot['path'])
            if hashlib.sha256(raw).hexdigest() != slot['sha256'] or len(raw) != slot['bytes']:
                continue
            file = self.fresh(); file.write_bytes(raw)
            try:
                self.tool('p6_public_guard_v1', 'g2', slot['seat'], file)
                out[str(slot['seat'])] = json.loads(raw)
            except (ProtocolError, ValueError):
                continue
        if own is not None:
            self.tool('p6_public_guard_v1', 'g2', self.seat, self.fresh(own))
            out[str(self.seat)] = own
        return out

    def pin_vote(self):
        p = self.private / 'snapshots.json'
        saved = json.loads(p.read_text()) if p.exists() else {}
        key = f'{self.r["quest"]}:{self.r["attempt"]}'
        if key in saved and saved[key] != self.snapshot:
            raise ProtocolError('Frozen vote snapshot changed')
        saved[key] = self.snapshot
        p.write_text(json.dumps(saved), encoding='utf-8')

    def frozen(self, quest, attempt):
        saved = json.loads((self.private / 'snapshots.json').read_text())
        try:
            return saved[f'{quest}:{attempt}']
        except KeyError:
            raise ProtocolError('Missing fixed complete-circle vote snapshot')

    def offer(self):
        state = self.private / 'mail-state.json'
        packet = self.private / 'offer.json'
        if not state.exists():
            value = self.attack.get('false_list') if self.evil else None
            if self.view['role'] == 'merlin':
                value = [s for s in range(1, 9) if s not in self.view['evil_seats']]
            self.tool('p4_mail_v1', 'init', 'g2', self.seat, ','.join(map(str, value)) if value else 'none', state)
        if not packet.exists():
            self.tool('p4_mail_v1', 'offer', state, self.work / 'access/id_bus', self.pem, packet)
        return json.loads(packet.read_text())

    def verified(self):
        p = self.private / 'verified.json'
        if p.exists():
            return json.loads(p.read_text())
        offers = self.reports('offer', snapshot=self.frozen(1, 1))
        entries = []
        for sender, packet in offers.items():
            sender = int(sender)
            if sender == self.seat:
                state = json.loads((self.private / 'mail-state.json').read_text())
                if state['commitment'] == packet['commitment'] and state['list']:
                    entries.append(dict(list=state['list'], source=sender))
                continue
            body = self.fresh()
            try:
                self.tool('p4_mail_v1', 'receive', 'g2', sender, self.seat, packet['commitment'], self.work / 'access/id_bus', self.pem / f'p{sender}.pem', self.fresh(packet), body)
                self.tool('p4_mail_v1', 'check', 'g2', sender, self.seat, packet['commitment'], body)
                value = json.loads(body.read_text())
                if 'list' in value:
                    entries.append(dict(list=value['list'], source=sender))
            except ProtocolError as exc:
                (self.private / f'receive-error-p{sender}.txt').write_text(str(exc), encoding='utf-8')
                continue
        value = dict(v=1, game='g2', seat=self.seat, verified=entries)
        p.write_text(json.dumps(value), encoding='utf-8')
        return value

    def selection(self, mode, data):
        output = self.fresh()
        self.tool('p1_selection_v1', mode, self.fresh(data), output)
        return json.loads(output.read_text())

    def initial(self, own=None):
        snapshot = self.snapshot if self.r['quest'] == 1 and self.r['attempt'] == 2 else self.frozen(1, 2)
        data = dict(game='g2', receipts=self.reports('receipt', snapshot=snapshot, own=own))
        plan = self.calc('p3_receipts_v1', data)
        if plan['status'] != 'ready':
            raise ProtocolError('invalid_premises: ' + plan['status'])
        return data, plan

    def recovery_context(self, plan):
        failures = [e for e in self.bulletin['events'] if e.get('event') == 'quest_result' and not e['passed']]
        if plan.get('branch') != 'A_in_three' or not failures:
            return None
        k = failures[0]['quest'] + 1
        return k, sum(e['quest'] >= k for e in failures)

    def recovery(self, plan, k, own=None):
        data = dict(game='g2', retained=plan['retained'], reports=self.reports('x_source', k, self.frozen(k, 1)))
        preliminary = self.calc('p2_recovery_v1', data)
        if preliminary['status'] == 'await_A_next_circle':
            snapshot = self.snapshot if self.r['quest'] == k and self.r['attempt'] == 2 else self.frozen(k, 2)
            choices = self.reports('x_choice', k, snapshot, own)
            if str(preliminary['A']) in choices:
                data['a_choice'] = choices[str(preliminary['A'])]
        return data, preliminary

    def reply(self):
        r = self.r
        if not r['eligible'] or r['submitted']:
            raise ProtocolError('Seat is not eligible for a new action')
        phase = r['phase']; action = {}; attachments = []
        def attach(kind, content, quest=1):
            name = f'g2_{kind}_' + (f'q{quest}_' if kind.startswith('x_') else '') + f'p{self.seat}.json'
            self.tool('p6_public_guard_v1', 'g2', self.seat, self.fresh(content))
            attachments.append(dict(path='artifacts/' + name, content=content))
        if phase == 'order': action = dict(direction='clockwise')
        elif phase == 'task':
            fail = self.attack.get('fail') or r['quest'] in self.attack.get('fail_quests', [])
            action = dict(card='fail' if self.evil and fail else 'success')
        elif phase == 'assassination':
            good = [s for s in range(1, 9) if s not in self.view['evil_seats']]
            action = dict(target=secrets.choice(good))
        elif phase in ('speech', 'vote'):
            q, a = r['quest'], r['attempt']
            if phase == 'vote': self.pin_vote()
            own = None
            preparing = q == 1 and a == 1
            if preparing and phase == 'speech': attach('offer', self.offer())
            if not preparing:
                if q == 1 and a == 2 and phase == 'speech':
                    own = self.selection('receipt', self.verified()); attach('receipt', own)
                # Earlier receipt speakers need no complete plan yet.
                need_plan = phase == 'vote' or r['leader'] == self.seat or q > 1 or a > 2
                if need_plan:
                    data, plan = self.initial(own)
                    context = self.recovery_context(plan)
                    if context:
                        k, failed = context
                        preparing = q == k and a == 1
                        if preparing and phase == 'speech':
                            X = next(l for l in plan['retained'] if plan['A'] not in l)
                            sources = [e['source'] for e in self.verified()['verified'] if e['list'] == X]
                            source = sources[0] if self.seat in X and sources else None
                            if self.evil and 'x_source' in self.attack:
                                source = self.attack['x_source']
                                if self.seat not in X or (source is not None and (type(source) is not int or source not in X)):
                                    raise ProtocolError('Attack source must be null or an X member, reported by an X member')
                            attach('x_source', dict(v=1, game='g2', phase='x_source', seat=self.seat, X=X, source=source), k)
                        if not preparing:
                            rd, rp = self.recovery(plan, k)
                            choice = None
                            if q == k and a == 2 and phase == 'speech' and rp['status'] == 'await_A_next_circle' and rp['A'] == self.seat:
                                private = self.verified().copy()
                                private['verified'] = [e for e in private['verified'] if e['list'] != rp['X']]
                                private['recovery'] = dict(X=rp['X'], excluded_source=rp['source'])
                                choice = self.selection('recovery', private); attach('x_choice', choice, k)
                            if phase == 'vote' or r['leader'] == self.seat:
                                rd, rp = self.recovery(plan, k, choice)
                                team = self.calc('p2_recovery_v1', rd, q, failed)['team']
                    else:
                        if phase == 'vote' or r['leader'] == self.seat:
                            team = self.calc('p3_receipts_v1', data, q, r['failures'])['team']
            if phase == 'speech' and r['leader'] == self.seat:
                action = dict(team=list(range(1, (3,4,4,5,5)[q-1] + 1)) if preparing else team)
            if phase == 'vote': action = dict(approve=False if preparing else sorted(r['team']) == sorted(team))
        elif phase != 'assassination_speech':
            raise ProtocolError('Unsupported phase')
        reply = dict(seen_snapshot=self.snapshot, action=action)
        if phase in ('speech', 'assassination_speech'):
            reply['message'] = dict(seat=self.seat, game_id='g2', stage=r['stage'], text=BROADCAST)
            reply['attachments'] = attachments
        return reply


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('workspace', 'request', 'public-repo', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--false-list', help='Evil only: comma-separated five seats')
    p.add_argument('--fail', action='store_true', help='Evil only: play Fail')
    args = p.parse_args()
    attack = None
    if args.false_list or args.fail:
        attack = dict(fail=args.fail)
        if args.false_list: attack['false_list'] = list(map(int, args.false_list.split(',')))
    # CLI dependency setup is shared with the bootstrap, never reads a room.
    from challenge import dependencies
    dependencies()
    result = Bot(args.workspace, args.request, args.public_repo, attack).reply()
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
