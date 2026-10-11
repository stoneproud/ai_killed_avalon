import json
from pathlib import Path
import tempfile
import unittest

from bot import Bot, ProtocolError, BROADCAST
from challenge import initialize, dependencies, export_seat, verify_vendor
from host import Host


class BotTests(unittest.TestCase):
    def test_own_report_only_fills_unoccupied_current_leader_slot(self):
        dependencies()
        with tempfile.TemporaryDirectory() as tmp:
            b = Bot.__new__(Bot); b.private=Path(tmp); b.seat=1; b.snapshot='b'*40
            b.r=dict(phase='speech',leader=1,eligible=True,submitted=False,quest=1,attempt=2,
                     stage='g2_q1_proposal2_speech_s8_p1')
            own=dict(v=1,game='g2',phase='receipt',seat=1,lists=[],four_choice=[])
            bulletin=dict(events=[],files=[])
            b.blob=lambda snapshot,path: json.dumps(bulletin).encode()
            self.assertEqual(b.reports('receipt',own=own), {'1':own})
            b.r['leader']=2
            with self.assertRaisesRegex(ProtocolError, 'last leader'):
                b.reports('receipt',own=own)
            b.r['leader']=1
            with self.assertRaisesRegex(ProtocolError, 'current window'):
                b.reports('receipt',snapshot='a'*40,own=own)
            bulletin['events']=[dict(event_id='first',by=1,stage='g2_q1_proposal2_speech_s8_p1',branch_commit='a'*40)]
            with self.assertRaisesRegex(ProtocolError, 'invalid first event'):
                b.reports('receipt',own=own)
            bulletin['events']=[]
            b.r.update(quest=2,stage='g2_q2_proposal2_speech_s8_p1')
            choice=dict(v=1,game='g2',phase='x_choice',seat=1,X=[4,5,6,7,8],excluded_source=4,choice=[1,2,3,6,7])
            self.assertEqual(b.reports('x_choice',quest=2,own=choice), {'1':choice})
            with self.assertRaisesRegex(ProtocolError, 'current window'):
                b.reports('receipt',quest=2,own=own)

    def test_attack_and_eligibility_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = dict(seat=1, private_view=dict(role='servant', faction='good'))
            with self.assertRaisesRegex(ProtocolError, 'Evil'):
                Bot(Path(tmp), request, Path(tmp), dict(fail=True))
        b = Bot.__new__(Bot)
        b.r = dict(eligible=True, submitted=False, phase='task')
        b.evil = False; b.attack = dict(fail=True); b.snapshot='a'*40
        self.assertEqual(b.reply()['action'], dict(card='success'))
        b.evil=True
        self.assertEqual(b.reply()['action'], dict(card='fail'))
        b.r['submitted']=True
        with self.assertRaisesRegex(ProtocolError, 'eligible'):
            b.reply()

    def test_original_selection_and_both_recovery_branches(self):
        dependencies()
        with tempfile.TemporaryDirectory() as tmp:
            b = Bot.__new__(Bot); b.private = Path(tmp)
            four = [[1,2,3,4,5],[1,2,3,6,7],[1,4,5,6,7],[1,2,4,6,8]]
            def receipts(lists, choice=None):
                return dict(game='g2', receipts={str(s):dict(v=1,game='g2',phase='receipt',seat=s,
                    lists=[l for l in lists if s in l],four_choice=choice if s==1 and choice else []) for s in range(1,9)})
            plan = b.calc('p3_receipts_v1', receipts(four, four[0]), 1, 0)
            self.assertEqual(plan['branch'], 'A_in_four')
            self.assertEqual(plan['team'], [1,2,3])
            four[3] = [2,3,4,6,8]
            plan = b.calc('p3_receipts_v1', receipts(four), 1, 0)
            self.assertEqual(plan['branch'], 'A_in_three')
            X = four[3]
            data = dict(game='g2', retained=four, reports={str(s):dict(v=1,game='g2',phase='x_source',seat=s,X=X,source=8) for s in X})
            waiting = b.calc('p2_recovery_v1', data)
            self.assertEqual(waiting['status'], 'await_A_next_circle')
            private = dict(v=1,game='g2',seat=1,verified=[dict(list=l,source=s) for l,s in zip(four[:3],[1,6,7])],recovery=dict(X=X,excluded_source=8))
            data['a_choice'] = b.selection('recovery', private)
            self.assertEqual(b.calc('p2_recovery_v1', data, 2, 0)['team'], [1,2,3,4])
            data.pop('a_choice'); data['reports'] = {}
            fallback = b.calc('p2_recovery_v1', data)
            self.assertEqual(fallback['status'], 'ready')
            self.assertEqual(fallback['branch'], 'unsplit_partition')
            self.assertEqual(len(fallback['ranges']), 2)
            b.bulletin = dict(events=[dict(event='quest_result',quest=1,passed=False),dict(event='quest_result',quest=2,passed=True),dict(event='quest_result',quest=3,passed=False)])
            self.assertEqual(b.recovery_context(plan), (2,1))

    def test_fresh_full_native_game(self):
        dependencies()
        verify_vendor()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'room'
            initialize(root)
            h = Host(root); h.deal()
            counts = {}; discussion = []
            for _ in range(250):
                h = Host(root)
                if h.s['phase'] == 'finished': break
                seat = next(n for n in h.expected() if str(n) not in h.s['pending'])
                exported = export_seat(root, seat)
                request = json.loads((exported / 'request.json').read_text())
                reply = Bot(root / 'players' / f'p{seat}', request, exported / 'public_repo').reply()
                counts[request['phase']] = counts.get(request['phase'], 0) + 1
                if 'message' in reply:
                    self.assertEqual(reply['message']['text'], BROADCAST)
                if request['phase'] == 'assassination_speech': discussion.append(seat)
                if request['phase'] == 'task': self.assertEqual(reply['action'], {'card':'success'})
                if request['phase'] == 'vote' and request['quest'] == 1 and request['attempt'] == 1:
                    self.assertFalse(reply['action']['approve'])
                h.submit(seat, reply)
            else: self.fail('Baseline did not finish')
            self.assertEqual(h.s['successes'], 3)
            self.assertEqual(h.s['failures'], 0)
            self.assertEqual(len(discussion), 3)
            self.assertEqual(counts['assassination'], 1)
            verify_vendor()


if __name__ == '__main__': unittest.main()
