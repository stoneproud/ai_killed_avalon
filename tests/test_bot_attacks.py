"""New-key, new-host end-to-end adapter fixtures; no original run is opened."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import uuid

from bot import Bot
from challenge import HERE, dependencies, initialize, run, verify_vendor
from host import Host


class AttackAdapterTests(unittest.TestCase):
    def fixture(self, callback):
        dependencies(); verify_vendor()
        with tempfile.TemporaryDirectory(prefix='sealed-adapter-attack-') as tmp:
            root = Path(tmp) / 'room'
            initialize(root)
            h = Host(root); h.deal()
            # Test-only deal override. No production role override or old keys.
            h.s['roles'] = dict(zip(map(str, range(1,9)),
                ['merlin','percival','servant','morgana','assassin','servant','servant','minion']))
            h.s['leader'] = 1
            h.s['bulletin']['events'][-1]['initial_leader'] = 1
            h.publish()
            public = Path(tmp) / 'published-only'
            run(['git','clone','--no-local','--single-branch','--branch','main','--no-checkout',h.repo,public])
            run(['git','-C',public,'remote','remove','origin'])
            log = []
            try:
                callback(root, public, log)
            except Exception:
                # Retain a failed NEW fixture, its private tool diagnostics and exact actions.
                evidence = HERE / 'work/challenge21_test_failures' / uuid.uuid4().hex
                evidence.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(root, evidence)
                (evidence / 'adapter-actions.json').write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding='utf-8')
                raise
            verify_vendor()

    def action(self, root, public, attacks, log, mutate=None):
        h = Host(root)
        seat = next(n for n in h.expected() if str(n) not in h.s['pending'])
        # Trusted test scheduler transfers only published main, and routes step to one seat.
        run(['git','-C',public,'fetch','--no-tags',h.repo,'main'])
        request = h.step(seat)
        bot = Bot(root / 'players' / f'p{seat}', request, public, attacks.get(seat))
        reply = bot.reply()
        if mutate: mutate(request, reply)
        log.append(dict(request=request, reply=copy.deepcopy(reply)))
        h.submit(seat, reply)
        return request, reply, bot

    def recovery_game(self, reported_source):
        def play(root, public, log):
            attacks = {
                4:dict(false_list=[4,5,6,7,8],fail_quests=[1,2] if reported_source == 5 else [1],x_source=reported_source),
                5:dict(false_list=[1,2,3,4,5],x_source=reported_source),
                8:dict(false_list=[1,2,4,6,8],x_source=reported_source),
            }
            first_plan = None; sources = {}; choices = []; preparation_votes = []
            for _ in range(250):
                h = Host(root)
                if h.s['phase'] == 'finished': break
                request, reply, b = self.action(root, public, attacks, log)
                q, a, phase = request['quest'], request['attempt'], request['phase']
                if phase == 'vote' and q == 1 and a == 2:
                    _, first_plan = b.initial()
                    self.assertEqual(first_plan['branch'], 'A_in_three')
                    self.assertEqual(first_plan['X'], [4,5,6,7,8])
                    self.assertEqual(request['team'], [4,5,6])
                if q == 2 and a == 1 and phase == 'vote':
                    preparation_votes.append(reply['action']['approve'])
                for attachment in reply.get('attachments', []):
                    content = attachment['content']
                    if content['phase'] == 'x_source':
                        self.assertEqual(q, 2); self.assertEqual(a, 1)
                        self.assertEqual(set(content), {'v','game','phase','seat','X','source'})
                        sources[request['seat']] = content['source']
                    elif content['phase'] == 'x_choice':
                        self.assertEqual(q, 2); self.assertEqual(a, 2)
                        self.assertEqual(request['seat'], 1)
                        self.assertEqual(set(content), {'v','game','phase','seat','X','excluded_source','choice'})
                        self.assertEqual(content['choice'], [1,2,3,6,7])
                        choices.append(content)
                if phase == 'vote' and q == 2 and a == 2:
                    data, preliminary = b.recovery(first_plan, 2)
                    ready = b.calc('p2_recovery_v1', data, 2, 0)
                    self.assertEqual(ready['branch'], 'four_source_agreement' if reported_source == 4 else 'unsplit_partition')
                    self.assertEqual(request['team'], ready['team'])
            else: self.fail('Attack fixture did not finish')
            h = Host(root)
            self.assertEqual(h.s['successes'], 3)
            self.assertEqual(h.s['failures'], 2 if reported_source == 5 else 1)
            self.assertEqual(sources, {1:None,2:None,3:None,4:reported_source,5:reported_source,6:4,7:4,8:reported_source})
            self.assertEqual(preparation_votes, [False]*8)
            self.assertEqual(len(choices), 1 if reported_source == 4 else 0)
            votes = [e for e in h.s['bulletin']['events'] if e['event'] == 'team_vote']
            self.assertEqual(sum(not e['approved'] for e in votes), 2)
            quest_results = [e for e in h.s['bulletin']['events'] if e['event'] == 'quest_result']
            self.assertEqual(quest_results[0]['fails'], 1)
            self.assertEqual(quest_results[0]['team'], [4,5,6])
            if reported_source == 5:
                self.assertFalse(quest_results[1]['passed'])
                self.assertEqual(quest_results[1]['team'], [1,2,3,4])
                self.assertEqual(quest_results[2]['team'], [1,2,3,6])
                self.assertTrue(all(e['passed'] for e in quest_results[2:]))
        self.fixture(play)

    def test_bad_three_report_five_unsplit_recovery(self):
        self.recovery_game(5)

    def test_bad_three_report_four_A_choice_recovery(self):
        self.recovery_game(4)

    def test_real_mail_A_in_four_complete_game(self):
        def play(root, public, log):
            h = Host(root)
            h.s['roles'] = dict(zip(map(str, range(1,9)),
                ['merlin','percival','servant','servant','servant','morgana','assassin','minion']))
            h.save()
            attacks = {6:dict(false_list=[1,2,3,6,7]),7:dict(false_list=[1,4,5,6,7]),8:dict(false_list=[1,2,4,6,8])}
            for _ in range(200):
                h = Host(root)
                if h.s['phase'] == 'finished': break
                request, reply, b = self.action(root, public, attacks, log)
                if request['phase'] == 'vote' and request['quest'] == 1 and request['attempt'] == 2:
                    _, plan = b.initial()
                    self.assertEqual(plan['branch'], 'A_in_four')
                    self.assertEqual(plan['ranges'], [[1,2,3,4,5]])
                    self.assertEqual(request['team'], [1,2,3])
                self.assertTrue(all(a['content']['phase'] in ('offer','receipt') for a in reply.get('attachments',[])))
            else: self.fail('A_in_four fixture did not finish')
            h = Host(root)
            self.assertEqual((h.s['successes'],h.s['failures']), (3,0))
        self.fixture(play)

    def test_invalid_first_offer_cannot_be_replaced_in_receipt_circle(self):
        def play(root, public, log):
            attacks = {4:dict(false_list=[4,5,6,7,8])}
            valid_offer = None
            def mutate(request, reply):
                nonlocal valid_offer
                if request['phase'] != 'speech': return
                if request['seat'] == 8 and request['quest'] == 1 and request['attempt'] == 1:
                    reply['attachments'] = []
                if request['seat'] != 4: return
                if request['quest'] == 1 and request['attempt'] == 1:
                    valid_offer = copy.deepcopy(reply['attachments'][0])
                    reply['attachments'][0]['content']['unapproved_extra'] = True
                if request['quest'] == 1 and request['attempt'] == 2:
                    reply['attachments'].append(valid_offer)
            for _ in range(100):
                h = Host(root)
                if h.s['phase'] == 'task': break
                request, reply, b = self.action(root, public, attacks, log, mutate)
                if request['phase'] == 'speech' and request['quest'] == 1 and request['attempt'] == 2:
                    self.assertTrue(all(e['source'] != 4 for e in b.verified()['verified']))
                    self.assertTrue(all(e['content']['phase'] == 'receipt' or request['seat'] == 4 for e in reply['attachments']))
                    for attachment in reply['attachments']:
                        if attachment['content']['phase'] == 'receipt':
                            self.assertEqual(set(attachment['content']), {'v','game','phase','seat','lists','four_choice'})
                if request['phase'] == 'vote' and request['attempt'] == 2:
                    self.assertNotIn('4', b.reports('offer', snapshot=b.frozen(1,1)))
                    self.assertNotIn('4', b.reports('offer', snapshot=b.snapshot))
                    self.assertNotIn('8', b.reports('offer', snapshot=b.frozen(1,1)))
            else: self.fail('No task after invalid Evil first offer')
            self.assertEqual(Host(root).s['team'], [1,2,3])
        self.fixture(play)


if __name__ == '__main__': unittest.main()
