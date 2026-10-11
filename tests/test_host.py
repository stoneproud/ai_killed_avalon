import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('challenge_host',Path(__file__).resolve().parents[1]/'host.py')
M=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)


class HostTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/'room'
        self.h=M.Host.init(self.root)

    def tearDown(self): self.temp.cleanup()

    def send(self,seat,action,attachments=None):
        h=self.h; value=dict(seen_snapshot=h.s['snapshot'],action=action)
        if h.s['phase'] in ('speech','assassination_speech'):
            value['message']=dict(seat=seat,stage=h.stage(),game_id='g2',text='fixed broadcast')
            value['attachments']=attachments or []
        return h.submit(seat,value)

    def proposal(self,team):
        self.send(self.h.s['leader'],{'direction':'clockwise'})
        for _ in range(8):
            n=self.h.expected()[0]
            self.send(n,{'team':team} if n==self.h.s['leader'] else {})

    def vote(self,approve=True):
        for n in M.SEATS:self.send(n,{'approve':approve})

    def cards(self,failers=()):
        for n in self.h.s['team']: self.send(n,{'card':'fail' if n in failers else 'success'})

    def fixed(self):
        self.h.deal()
        self.h.s['roles']={'1':'merlin','2':'percival','3':'servant','4':'servant','5':'servant','6':'morgana','7':'assassin','8':'minion'}
        self.h.s['leader']=1; self.h.save()

    def test_fresh_predeal_and_once(self):
        self.assertNotIn('roles',self.h.s)
        self.assertEqual(self.h.status()['phase'],'predeal')
        self.assertEqual(len(list((self.root/'players').iterdir())),8)
        self.assertEqual(len(self.h.s['snapshot']),40)
        self.h.deal()
        roles=list(self.h.s['roles'].values())
        self.assertEqual(roles.count('servant'),3)
        with self.assertRaises(ValueError):self.h.deal()
        with self.assertRaises(ValueError):M.Host.init(self.root)

    def test_publication_metadata_and_restart(self):
        self.fixed();self.send(1,{'direction':'clockwise'})
        self.assertEqual(self.h.s['order'],[2,3,4,5,6,7,8,1])
        stage=self.h.stage()
        self.send(2,{},[{'path':'artifacts/g2_offer_p2.json','content':{'v':1}}])
        b=json.loads(self.h.git('show',self.h.s['snapshot']+':public/bulletin.json'))
        e=b['events'][-1]; f=b['files'][-1]
        self.assertEqual(e['stage'],stage);self.assertEqual(e['by'],2)
        self.assertEqual(f['source_commit'],e['branch_commit'])
        self.assertEqual(f['path'],'public/files/p2/artifacts/g2_offer_p2.json')
        self.assertEqual(json.loads(self.h.git('show',e['branch_commit']+':artifacts/g2_offer_p2.json')),{'v':1})
        self.h=M.Host(self.root)
        self.assertEqual(self.h.expected(),[3])

    def test_secret_barrier_duplicate_and_stale(self):
        self.fixed(); self.proposal([1,2,3]); snap=self.h.s['snapshot']
        self.send(1,{'approve':False})
        self.assertEqual(self.h.s['snapshot'],snap)
        self.assertNotIn('pending',self.h.status())
        self.assertFalse(self.h.step(2)['submitted'])
        with self.assertRaises(ValueError):self.send(1,{'approve':True})
        self.h=M.Host(self.root)
        for n in range(2,9):self.send(n,{'approve':True})
        self.assertEqual(self.h.s['phase'],'task')
        with self.assertRaises(ValueError):self.h.submit(1,{'seen_snapshot':snap,'action':{'card':'success'}})
        new=self.h.s['snapshot'];self.send(1,{'card':'success'})
        self.assertEqual(self.h.s['snapshot'],new)
        with self.assertRaises(ValueError):self.send(2,{'card':'fail'})
        self.send(2,{'card':'success'});self.send(3,{'card':'success'})
        result=self.h.s['bulletin']['events'][-1]
        self.assertEqual(result['event'],'quest_result');self.assertNotIn('cards',result)

    def test_five_rejections(self):
        self.fixed()
        for _ in range(5):self.proposal([1,2,3]);self.vote(False)
        self.assertEqual(self.h.s['result']['reason'],'five_consecutive_rejected_teams')

    def test_three_fails(self):
        self.fixed()
        for size in [3,4,4]:
            self.proposal([6]+list(range(1,size)));self.vote();self.cards([6])
        self.assertEqual(self.h.s['result']['reason'],'three_failed_quests')

    def test_fourth_single_fail_and_assassination(self):
        self.fixed()
        for size,fail in [(3,True),(4,True),(4,False),(5,True),(5,False)]:
            self.proposal([6]+list(range(1,size)));self.vote();self.cards([6] if fail else [])
        quests=[e for e in self.h.s['bulletin']['events'] if e['event']=='quest_result']
        self.assertTrue(quests[3]['passed']);self.assertEqual(quests[3]['fails'],1)
        self.assertEqual(self.h.s['phase'],'assassination_speech')
        for _ in range(3):self.send(self.h.expected()[0],{})
        with self.assertRaises(ValueError):self.send(7,{'target':6})
        self.send(7,{'target':1})
        self.assertEqual(self.h.s['result']['winner'],'evil')

    def test_assassin_miss(self):
        self.fixed()
        for size in [3,4,4]:
            self.proposal(list(range(1,size+1)));self.vote();self.cards()
        for _ in range(3):self.send(self.h.expected()[0],{})
        self.send(7,{'target':2});self.assertEqual(self.h.s['result']['winner'],'good')

    def test_invalid_inputs_no_publication(self):
        self.fixed();self.send(1,{'direction':'counterclockwise'})
        snap=self.h.s['snapshot'];n=self.h.expected()[0]
        with self.assertRaises(ValueError):self.send(n,{},[{'path':'artifacts/../secret.json','content':{}}])
        self.assertEqual(self.h.s['snapshot'],snap)
        with self.assertRaises(ValueError):self.send(n,{'team':[1,2,3]})

    def test_publication_journal_recovery(self):
        self.fixed(); state=json.loads(json.dumps(self.h.s))
        state['attempt']=2
        M.atomic(self.root/'pending.json',state)
        recovered=M.Host(self.root)
        self.assertEqual(recovered.s['attempt'],2)
        self.assertFalse((self.root/'pending.json').exists())

    def test_untrusted_json_types_and_cross_platform_paths(self):
        self.fixed();self.h.s['leader']=8
        self.send(8,{'direction':'clockwise'})
        snapshot=self.h.s['snapshot'];stage=self.h.stage()
        value={'seen_snapshot':snapshot,'action':{},'message':{'seat':True,'game_id':'g2','stage':stage}}
        with self.assertRaises(ValueError):self.h.submit(1,value)
        value['message']['seat']=1
        for path in ['artifacts/.git/config.json','artifacts/con.json','artifacts/NUL.txt.json','artifacts/a:b.json','artifacts/../x.json','artifacts/dir./x.json','artifacts/a\\b.json','artifacts/a\nx.json']:
            value['attachments']=[{'path':path,'content':{}}]
            with self.subTest(path=path),self.assertRaises(ValueError):self.h.submit(1,value)
        value['attachments']=[{'path':'artifacts/x.json','content':float('nan')}]
        with self.assertRaises(ValueError):self.h.submit(1,value)
        value['attachments']=[{'path':'artifacts/x.json','content':{}},{'path':'artifacts/X.json','content':{}}]
        with self.assertRaises(ValueError):self.h.submit(1,value)
        value['attachments']=[];value['message']['text']='a'*65536
        with self.assertRaises(ValueError):self.h.submit(1,value)
        self.assertEqual(self.h.s['snapshot'],snapshot)
        self.assertEqual(self.h.git('rev-parse','main'),snapshot)
        for bad in [True,[],None,'1']:
            with self.subTest(seat=bad),self.assertRaises(ValueError):self.h.submit(bad,{})

    def test_no_secret_scheduler_role_leak(self):
        self.fixed()
        self.h.s.update(phase='assassination_speech',order=[6,7,8],speech_index=0)
        status=self.h.status()
        self.assertNotIn('eligible_seats',status)
        self.assertEqual(status['stage'],'g2_assassination_discussion1')
        request=self.h.step(2)
        self.assertNotIn('eligible_seats',request)
        self.assertNotIn('_p6',request['stage'])
        self.assertEqual(request['private_view'],{'role':'percival','faction':'good','merlin_or_morgana':[1,6]})
        self.assertFalse(request['eligible'])
        self.assertEqual(self.h.step(6)['stage'],'g2_assassination_discussion1_s1_p6')
        self.h.s['phase']='assassination'
        self.assertNotIn('eligible_seats',self.h.status())
        self.assertFalse(self.h.step(6)['eligible'])
        self.assertTrue(self.h.step(7)['eligible'])
        self.assertNotIn('roles',self.h.status())

    def test_dict_list_boolean_actions_rejected(self):
        self.fixed()
        for bad in [{'direction':[]}, {'direction':True}, [], None]:
            with self.subTest(action=bad),self.assertRaises(ValueError):
                self.h.submit(1,{'seen_snapshot':self.h.s['snapshot'],'action':bad})
        self.proposal([1,2,3])
        for bad in [{'approve':1},{'approve':'true'},{'approve':[]},{'approve':True,'extra':False}]:
            with self.subTest(action=bad),self.assertRaises(ValueError):self.send(1,bad)
        self.assertEqual(self.h.s['pending'],{})

    def test_vote_ack_and_other_seat_request_do_not_reveal_partial(self):
        self.fixed();self.proposal([1,2,3])
        before=self.h.status();request=self.h.step(2)
        ack=self.send(1,{'approve':False})
        self.assertEqual(before,self.h.status())
        self.assertEqual(request,self.h.step(2))
        self.assertEqual(set(ack),{'accepted','seat','stage','snapshot'})
        self.assertNotIn('False',json.dumps(ack))
        b=json.loads(self.h.git('show',ack['snapshot']+':public/bulletin.json'))
        self.assertFalse(any(e['event']=='team_vote' for e in b['events']))


if __name__=='__main__':unittest.main()
