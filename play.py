"""Run the packaged baseline one seat action at a time, with no model calls.

Stops before a requested stage so a human/AI can take over. Never deals cards.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import uuid
from challenge import HERE, dependencies, export_seat, read_reply, sandbox
from host import Host, locked


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--until',help='Stop BEFORE this exact stage, e.g. g2_q1_vote2')
    p.add_argument('--max-actions',type=int,default=250)
    p.add_argument('--native-trusted',action='store_true',help='Run only our trusted baseline locally; never arbitrary attacker code')
    a=p.parse_args();root=a.root.resolve();dependencies()
    for count in range(a.max_actions):
        with locked(root):
            h=Host(root)
            if h.s['phase'] in ('predeal','finished') or h.stage()==a.until:
                print(json.dumps({'stopped':h.status(),'actions_this_run':count},ensure_ascii=False));return
            seats=[n for n in h.expected() if str(n) not in h.s['pending']]
            seat=seats[0]
        if a.native_trusted:
            exported=export_seat(root,seat)
            reply=root/'players'/f'p{seat}'/('reply-'+uuid.uuid4().hex+'.json')
            subprocess.run([sys.executable,str(HERE/'bot.py'),'--workspace',str(reply.parent),
                            '--request',str(exported/'request.json'),'--public-repo',str(exported/'public_repo'),
                            '--output',str(reply)],check=True)
        else:
            reply=Path(sandbox(root,seat)['reply'])
        with locked(root):
            h=Host(root)
            prior=h.s['phase'];h.submit(seat,read_reply(reply))
            # No full deal or partial secret values in progress output.
            print(json.dumps({'action_number':count+1,'stage_after':h.status()['stage'],
                              'phase_after':h.s['phase']},ensure_ascii=False),flush=True)
    raise RuntimeError('Action limit reached; room saved, no retry/redeal performed')


if __name__=='__main__': main()
