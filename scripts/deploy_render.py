"""Deploy a reviewed, CI-passing commit to Render and verify the resulting service."""
import json
import os
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(url: str, token: str, data: dict | None = None) -> dict:
    request = Request(url, data=json.dumps(data).encode() if data is not None else None,
                      headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json',
                               'Content-Type': 'application/json'})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def verify_commit(sha: str) -> None:
    if not re.fullmatch(r'[0-9a-fA-F]{40}', sha):
        raise ValueError('A full commit SHA is required.')
    sha = sha.lower()
    subprocess.run(['git', 'fetch', 'origin', 'master'], check=True, capture_output=True)
    subprocess.run(['git', 'merge-base', '--is-ancestor', sha, 'origin/master'],
                   check=True, capture_output=True)
    repo = os.environ['GITHUB_REPOSITORY']
    runs = request_json(f'https://api.github.com/repos/{repo}/actions/workflows/ci.yml/runs'
                        f'?head_sha={sha}&event=push&branch=master&per_page=100',
                        os.environ['GITHUB_TOKEN'])['workflow_runs']
    if not any(run['head_sha'] == sha and run['head_branch'] == 'master'
               and run['event'] == 'push' and run['conclusion'] == 'success' for run in runs):
        raise ValueError('The selected master commit has no successful push CI run.')


def main() -> None:
    sha = os.environ['DEPLOY_COMMIT'].lower()
    verify_commit(sha)
    token, service = os.environ['RENDER_API_KEY'], os.environ['RENDER_SERVICE_ID']
    if not re.fullmatch(r'srv-[a-zA-Z0-9]+', service):
        raise ValueError('Invalid Render service identifier.')
    base = f'https://api.render.com/v1/services/{service}'
    # Render supports commitId for Git-backed Docker services; never deploy a moving ref.
    deploy = request_json(base + '/deploys', token, {'commitId': sha})
    deploy_id = deploy['id']
    if not re.fullmatch(r'dep-[a-zA-Z0-9]+', deploy_id):
        raise ValueError('Invalid Render deployment identifier.')
    deadline = time.monotonic() + 900
    while True:
        deploy = request_json(base + '/deploys/' + deploy_id, token)
        if deploy.get('commit', {}).get('id') != sha:
            raise ValueError('Render deployment commit does not match the selected commit.')
        status = deploy['status']
        if status == 'live':
            break
        if status in {'build_failed', 'update_failed', 'pre_deploy_failed', 'canceled', 'deactivated'}:
            raise ValueError('Render deployment failed; inspect the provider dashboard.')
        if time.monotonic() >= deadline:
            raise ValueError('Render deployment did not become live within 15 minutes.')
        time.sleep(10)
    service_data = request_json(base, token)
    origin = service_data['serviceDetails']['url'].rstrip('/')
    if not re.fullmatch(r'https://[a-zA-Z0-9.-]+', origin):
        raise ValueError('Invalid Render service origin.')
    for path, expected in [('/api/health', {'status': 'ok'}),
                           ('/api/health/database', {'status': 'ready'})]:
        if request_json(origin + path, '', None) != expected:
            raise ValueError('Application health verification failed.')
    with urlopen(Request(origin + '/login', headers={'Accept': 'text/html'}), timeout=30) as response:
        if response.status != 200 or 'text/html' not in response.headers.get('Content-Type', ''):
            raise ValueError('Application frontend verification failed.')
    print(f'Verified deployment {sha} at {origin}')


if __name__ == '__main__':
    try:
        main()
    except (KeyError, ValueError, HTTPError, URLError, TimeoutError, subprocess.CalledProcessError):
        # Do not echo provider responses, request headers or credential-bearing URLs.
        print('Deployment failed. Check CI, secure configuration and the Render dashboard.', file=sys.stderr)
        raise SystemExit(1) from None
