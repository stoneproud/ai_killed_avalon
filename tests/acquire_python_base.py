"""Optional official OCI archive fetch on the trusted build host (never players).

Uses urllib's configured system proxy, no account credentials. Blob hashes are
checked against the HTTPS registry manifest. Does not alter proxy configuration.
"""
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.parse
import urllib.request


def acquire(output):
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    token_url='https://auth.docker.io/token?'+urllib.parse.urlencode(dict(service='registry.docker.io',scope='repository:library/python:pull'))
    with urllib.request.urlopen(token_url,timeout=60) as response:
        token=json.load(response)['token']
    base='https://registry-1.docker.io/v2/library/python/'
    accept=', '.join(['application/vnd.oci.image.index.v1+json','application/vnd.docker.distribution.manifest.list.v2+json','application/vnd.oci.image.manifest.v1+json','application/vnd.docker.distribution.manifest.v2+json'])
    def get(path):
        request=urllib.request.Request(base+path,headers={'Authorization':'Bearer '+token,'Accept':accept})
        with urllib.request.urlopen(request,timeout=120) as response:
            return response.read()
    index_raw=get('manifests/3.11-slim-bookworm')
    index=json.loads(index_raw)
    descriptor=next(d for d in index['manifests'] if d.get('platform',{}).get('os')=='linux' and d['platform'].get('architecture')=='amd64')
    manifest_raw=get('manifests/'+descriptor['digest'])
    assert 'sha256:'+hashlib.sha256(manifest_raw).hexdigest()==descriptor['digest']
    manifest=json.loads(manifest_raw)
    layout=output/'layout'; blobs=layout/'blobs/sha256'; blobs.mkdir(parents=True)
    (blobs/descriptor['digest'].split(':')[1]).write_bytes(manifest_raw)
    checked=[]
    for item in [manifest['config'],*manifest['layers']]:
        raw=get('blobs/'+item['digest'])
        if 'sha256:'+hashlib.sha256(raw).hexdigest()!=item['digest'] or len(raw)!=item['size']:
            raise RuntimeError('Official registry blob hash/size mismatch')
        (blobs/item['digest'].split(':')[1]).write_bytes(raw)
        checked.append(dict(digest=item['digest'],bytes=len(raw)))
        print(json.dumps(dict(blob=item['digest'],bytes=len(raw))),flush=True)
    descriptor=dict(descriptor)
    descriptor['annotations']={'org.opencontainers.image.ref.name':'docker.io/library/python:3.11-slim-bookworm'}
    (layout/'index.json').write_text(json.dumps(dict(schemaVersion=2,manifests=[descriptor])),encoding='utf-8')
    (layout/'oci-layout').write_text(json.dumps({'imageLayoutVersion':'1.0.0'}),encoding='utf-8')
    archive=output/'python-base.oci.tar'
    with tarfile.open(archive,'w') as stream:
        for p in layout.rglob('*'):
            if p.is_file(): stream.add(p,arcname=p.relative_to(layout).as_posix())
    evidence=dict(source='Official public Docker Hub library/python',tag='3.11-slim-bookworm',platform='linux/amd64',index_sha256=hashlib.sha256(index_raw).hexdigest(),manifest_digest=descriptor['digest'],config_digest=manifest['config']['digest'],checked_blobs=checked,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),proxy_credentials_logged=False)
    (output/'acquisition.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(archive=str(archive),manifest_digest=descriptor['digest'])),flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True)
    acquire(p.parse_args().output)
