import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import challenge
from host import Host


class SetupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / 'fresh'
        cls.status = challenge.initialize(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_predeal_keys_registration(self):
        self.assertEqual(self.status['phase'],'predeal')
        h=Host(self.root)
        self.assertNotIn('roles',h.s)
        keys=[]
        registration=json.loads((self.root/'setup_complete.json').read_bytes())['registration']
        for seat in range(1,9):
            work=self.root/'players'/f'p{seat}'
            keys.append(hashlib.sha256((work/'access/id_bus').read_bytes()).hexdigest())
            self.assertFalse((work/'private/offer_state.json').exists())
            pem=(work/'registered_pem'/f'p{seat}.pem').read_bytes()
            self.assertEqual(hashlib.sha256(pem).hexdigest(),registration['registered_public_keys'][seat-1]['pem_sha256'])
        self.assertEqual(len(set(keys)),8)

    def test_export_never_includes_hidden_git_objects(self):
        h=Host(self.root)
        secret=h.git('hash-object','-w','--stdin',data=b'SYNTHETIC_HOST_ONLY_SENTINEL')
        # An orphan host blob must not cross the publication boundary.
        exported=challenge.export_seat(self.root,1)
        repo=exported/'public_repo'
        found=subprocess.run(['git','-C',str(repo),'cat-file','-e',secret],capture_output=True)
        self.assertNotEqual(found.returncode,0)
        self.assertEqual(challenge.run(['git','-C',repo,'rev-parse','HEAD']).decode().strip(),h.s['snapshot'])
        self.assertEqual(challenge.run(['git','-C',repo,'remote']).strip(),b'')
        req=json.loads((exported/'request.json').read_bytes())
        self.assertEqual(req['seat'],1)
        self.assertNotIn('private_view',req)
        paths=challenge.run(['git','-C',repo,'ls-tree','-r','--name-only','HEAD']).decode()
        self.assertNotIn('id_bus',paths)

    def test_no_overwrite(self):
        with self.assertRaises(ValueError): challenge.initialize(self.root)


if __name__=='__main__': unittest.main()
