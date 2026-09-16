"""Launch only after source-bound reports cover the mandatory regression set."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET


def verdict(path, *, runtime=None):
    from release_evidence import summary, verify
    result = summary(path)
    if runtime is None:
        return {**result, 'passed': False, 'reason': 'source_binding_and_required_tests_not_checked'}
    return verify([path], runtime)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--junit',required=True,action='append'); parser.add_argument('--wait-seconds',type=int,default=1200)
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--subscription-xhigh', action='store_true')
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args(); command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not command: parser.error('Explicit child command required')
    deadline=time.monotonic()+args.wait_seconds
    print(json.dumps({'kind':'waiting_for_free_test_gate','junit':args.junit}),flush=True)
    while True:
        try:
            from release_evidence import verify
            result=verify(args.junit,args.runtime,subscription_xhigh=args.subscription_xhigh)
        except (FileNotFoundError,ET.ParseError):
            if time.monotonic()>=deadline: raise TimeoutError('No complete test report; no launch')
            time.sleep(5); continue
        print(json.dumps({'kind':'free_test_gate',**result}),flush=True)
        if not result['passed']: raise SystemExit('Test gate failed; no launch')
        raise SystemExit(subprocess.run(command,check=False).returncode)
