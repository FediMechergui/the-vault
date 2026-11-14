"""Validate live TLS, service readiness, PostgreSQL, Redis and a real gRPC frame.

Creates a disposable non-biometric account and deletes it in finally. No frames
or biometric templates are persisted; input is an in-memory blank JPEG.
"""
import argparse
import asyncio
import io
import json
import secrets
import ssl
import struct
import time
from pathlib import Path
import httpx
from PIL import Image
from websockets.asyncio.client import connect


async def run(base, output='docs/stack-smoke.json'):
    context = ssl.create_default_context(cafile='infra/certs/server.pem')
    async with httpx.AsyncClient(base_url=base, verify=context, timeout=30) as client:
        health = await client.get('/api/v1/health')
        health.raise_for_status()
        assert health.json()['ready'], health.text
        account = await client.post('/api/v1/users', json={'pseudo': 'smoke_' + secrets.token_hex(4), 'consent': True})
        account.raise_for_status()
        data = account.json()
        headers = {'Authorization': 'Bearer ' + data['management_token']}
        report = {'health': health.json()}
        try:
            denied = await client.get('/api/v1/vault', headers=headers)
            assert denied.status_code == 401
            result = await client.post('/api/v1/enroll/hand/start', headers=headers, json={'user_id': data['id']})
            result.raise_for_status()
            session = result.json()
            jpeg = io.BytesIO()
            Image.new('RGB', (640, 480), (120, 120, 120)).save(jpeg, format='JPEG', quality=70)
            async with connect(base.replace('https://', 'wss://') + '/ws/stream/' + session['session_id'], ssl=context) as ws:
                await ws.send(json.dumps({'token': session['session_token']}))
                assert json.loads(await ws.recv())['type'] == 'ready'
                started = time.perf_counter()
                await ws.send(struct.pack('>IQ', 1, int(time.time() * 1000)) + jpeg.getvalue())
                feedback = json.loads(await asyncio.wait_for(ws.recv(), 15))
                assert feedback['type'] == 'tracking', feedback
                assert feedback['quality'] is False
                report['blank_frame'] = {'correctly_rejected': True,
                    'first_frame_round_trip_ms': (time.perf_counter() - started) * 1000,
                    'server_ms': feedback['latency_ms']}
        finally:
            deleted = await client.delete('/api/v1/users/' + data['id'], headers=headers)
            deleted.raise_for_status()
        revoked = await client.get('/api/v1/users/me', headers=headers)
        assert revoked.status_code == 401
        report['credential_revoked_after_deletion'] = True
        Path(output).write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://localhost:8443')
    parser.add_argument('--output', default='docs/stack-smoke.json')
    args = parser.parse_args()
    asyncio.run(run(args.url, args.output))
