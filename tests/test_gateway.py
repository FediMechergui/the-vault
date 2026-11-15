import base64
import json
import struct
import time
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from gateway.app.main import create_app
from gateway.app.config import Settings
from gateway.app.storage import Template, User, Attempt
from gateway.app.state import observe_liveness
from vault_core import scoring
from .samples import capture


class FakeVision:
    """Test-only landmark source. Production always decodes JPEG through MediaPipe."""
    async def health(self): return {'ready': True}
    async def release(self, sid): pass
    async def close(self): pass
    async def extract(self, sid, layer, jpeg, timestamp):
        i = int(jpeg.decode())
        pinched = i in (1, 49)
        phase = max(0, i - 2) / 46 * np.pi * 2
        return {'quality': True, 'pinch': pinched, 'features': [.5 + .16 * np.cos(phase), .5 + .12 * np.sin(phase), 0],
                'landmarks': [[.5, .5, 0]] * 21, 'message': 'tracked', 'gesture': 'pinch' if pinched else 'pointing'}


class ReferenceScorer:
    fail = False
    async def health(self): return {'ready': True, 'engine': 'python-reference'}
    async def close(self): pass
    async def call(self, operation, layer, **payload):
        if operation == 'enroll': return {'template': scoring.enroll(layer, payload['captures']), 'engine': 'python-reference'}
        result = scoring.score(layer, **payload)
        if self.fail: result.update(passed=False, score=.1)
        return {**result, 'engine': 'python-reference'}


@pytest.fixture
def env(tmp_path):
    config = Settings(database_url=f'sqlite:///{tmp_path / "test.db"}', redis_url='',
        jwt_secret='j' * 64, encryption_key='ab' * 32, admin_key='a' * 64, s3_endpoint='')
    scorer = ReferenceScorer()
    app = create_app(config, FakeVision(), scorer)
    with TestClient(app) as client:
        yield client, app, scorer


def user(client, name='tester'):
    reply = client.post('/api/v1/users', json={'pseudo': name, 'consent': True})
    assert reply.status_code == 201
    data = reply.json()
    return data, {'Authorization': 'Bearer ' + data['management_token']}


def insert_capture(client, app, sid, layer, repetitions):
    state = client.portal.call(app.state.sessions.get, sid)
    state['captures'] = [capture(layer, i) for i in range(repetitions)]
    state['status'] = 'captured'
    client.portal.call(app.state.sessions.put, sid, state)


def enroll_hand(client, app, account, headers):
    client.put(f"/api/v1/users/{account['id']}/sequence", headers=headers, json={'layers': ['hand']})
    session = client.post('/api/v1/enroll/hand/start', headers=headers, json={'user_id': account['id']}).json()
    insert_capture(client, app, session['session_id'], 'hand', 5)
    response = client.post('/api/v1/enroll/hand/commit', headers=headers, json={'session_id': session['session_id']})
    assert response.status_code == 200, response.text


def test_consent_scope_ownership_and_sequence(env):
    client, app, _ = env
    assert client.post('/api/v1/users', json={'pseudo': 'no', 'consent': False}).status_code == 422
    account, headers = user(client)
    other, other_headers = user(client, 'other')
    assert client.get('/api/v1/vault', headers=headers).status_code == 401
    assert client.delete(f"/api/v1/users/{account['id']}", headers=other_headers).status_code == 403
    assert client.put(f"/api/v1/users/{account['id']}/sequence", headers=headers, json={'layers': ['hand', 'hand']}).status_code == 422
    assert client.post('/api/v1/auth/start', json={'user_id': account['id']}).status_code == 409
    assert client.get('/api/v1/admin/attempts').status_code == 401


def test_incomplete_enrollment_and_encryption(env):
    client, app, _ = env
    account, headers = user(client)
    session = client.post('/api/v1/enroll/hand/start', headers=headers, json={'user_id': account['id']}).json()
    assert client.post('/api/v1/enroll/hand/commit', headers=headers, json={'session_id': session['session_id']}).status_code == 422
    enroll_hand(client, app, account, headers)
    with app.state.database.session() as db:
        template = db.get(Template, (account['id'], 'hand'))
        assert b'samples' not in template.features
        assert app.state.database.decrypt(template)['layer'] == 'hand'
        template.user_id = 'different-user'
        with pytest.raises(Exception): app.state.database.decrypt(template)


def test_unlock_token_and_delete_revoke_everything(env):
    client, app, _ = env
    account, headers = user(client)
    enroll_hand(client, app, account, headers)
    session = client.post('/api/v1/auth/start', json={'user_id': account['id']}).json()
    sid = session['session_id']
    session_headers = {'X-Session-Token': session['session_token']}
    assert client.post(f'/api/v1/auth/{sid}/next', headers=session_headers).status_code == 409
    insert_capture(client, app, sid, 'hand', 1)
    reply = client.post(f'/api/v1/auth/{sid}/next', headers=session_headers)
    assert reply.status_code == 200, reply.text
    assert reply.json()['status'] == 'unlocked'
    access = {'Authorization': 'Bearer ' + reply.json()['access_token']}
    vault = client.get('/api/v1/vault', headers=access)
    assert vault.json()['transparency']['fictional']
    assert client.get(vault.json()['meme_url']).status_code == 200
    assert client.post(f'/api/v1/auth/{sid}/next', headers=session_headers).status_code == 401
    assert client.delete(f"/api/v1/users/{account['id']}", headers=headers).status_code == 204
    assert client.get('/api/v1/vault', headers=access).status_code == 401
    assert client.get(vault.json()['meme_url']).status_code == 401
    with app.state.database.session() as db:
        assert db.get(User, account['id']) is None
        assert list(db.scalars(select(Template))) == []
        assert list(db.scalars(select(Attempt))) == []


def test_three_failures_lock_account_and_expiry_resets(env):
    client, app, scorer = env
    account, headers = user(client)
    enroll_hand(client, app, account, headers)
    scorer.fail = True
    for _ in range(3):
        session = client.post('/api/v1/auth/start', json={'user_id': account['id']}).json()
        insert_capture(client, app, session['session_id'], 'hand', 1)
        reply = client.post(f"/api/v1/auth/{session['session_id']}/next", headers={'X-Session-Token': session['session_token']})
        assert reply.json()['status'] == 'failed'
    assert client.post('/api/v1/auth/start', json={'user_id': account['id']}).status_code == 423
    with app.state.database.session.begin() as db:
        db.get(User, account['id']).locked_until = time.time() - 1
    assert client.post('/api/v1/auth/start', json={'user_id': account['id']}).status_code == 200
    with app.state.database.session() as db:
        assert db.get(User, account['id']).failures == 0


def test_websocket_binary_frames_pinches_repetitions_and_replay(env):
    client, app, _ = env
    account, headers = user(client)
    session = client.post('/api/v1/enroll/hand/start', headers=headers, json={'user_id': account['id']}).json()
    async def unrestricted_test_rate(*args, **kwargs): return True
    app.state.sessions.rate_limit = unrestricted_test_rate
    with client.websocket_connect('/ws/stream/' + session['session_id']) as ws:
        ws.send_json({'token': session['session_token']})
        assert ws.receive_json()['type'] == 'ready'
        frame_id = 0
        for repetition in range(5):
            ws.send_json({'type': 'begin'})
            assert ws.receive_json()['type'] == 'capturing'
            for i in range(50):
                frame_id += 1
                packet = struct.pack('>IQ', frame_id, frame_id * 67) + str(i).zfill(8).encode()
                ws.send_bytes(packet)
                tracking = ws.receive_json()
                assert tracking['type'] == 'tracking'
            assert tracking['trace_done']
            ws.send_bytes(packet)
            assert ws.receive_json()['type'] == 'error'
            ws.send_json({'type': 'finish'})
            done = ws.receive_json()
            assert done['type'] == 'captured', done
            assert done['completed'] == repetition + 1
        assert done['ready_to_commit']
    reply = client.post('/api/v1/enroll/hand/commit', headers=headers, json={'session_id': session['session_id']})
    assert reply.status_code == 200, reply.text


def test_liveness_needs_complete_random_action_and_depth():
    state = {'live_challenge': 'blink_twice', 'live_count': 0, 'live_closed': False}
    assert not observe_liveness(state, {'blink': 1, 'depth_ok': False})
    assert not observe_liveness(state, {'blink': 0, 'depth_ok': True})
    assert not observe_liveness(state, {'blink': 1, 'depth_ok': True})
    assert not observe_liveness(state, {'blink': 0, 'depth_ok': True})
    assert not observe_liveness(state, {'blink': 1, 'depth_ok': True})
    assert observe_liveness(state, {'blink': 0, 'depth_ok': True})
    state = {'live_challenge': 'turn_left', 'live_centered': False}
    assert not observe_liveness(state, {'depth_ok': True, 'yaw': -.4})
    assert not observe_liveness(state, {'depth_ok': True, 'yaw': 0})
    assert observe_liveness(state, {'depth_ok': True, 'yaw': -.4})


@pytest.mark.parametrize('failure', ['timeout', 'unexpected'])
def test_transient_vision_failure_keeps_stream_open_and_recovers(env, monkeypatch, failure):
    from gateway.app.errors import VisionFailure
    original = FakeVision.extract
    calls = 0

    async def flaky(self, *args):
        nonlocal calls
        calls += 1
        if calls == 1:
            if failure == 'timeout':
                raise VisionFailure('vision_timeout', 'Gesture processing took too long.')
            raise RuntimeError('internal detail must not reach the phone')
        return await original(self, *args)

    monkeypatch.setattr(FakeVision, 'extract', flaky)
    client, app, _ = env
    account, headers = user(client)
    session = client.post('/api/v1/enroll/hand/start', headers=headers,
        json={'user_id': account['id']}).json()
    with client.websocket_connect('/ws/stream/' + session['session_id']) as ws:
        ws.send_json({'token': session['session_token']})
        assert ws.receive_json()['type'] == 'ready'
        ws.send_bytes(struct.pack('>IQ', 1, 1000) + b'00000000')
        error = ws.receive_json()
        assert error['type'] == 'error' and error['retryable'] is True
        assert error['code'] == ('vision_timeout' if failure == 'timeout' else 'vision_unavailable')
        assert 'internal detail' not in json.dumps(error)
        ws.send_bytes(struct.pack('>IQ', 2, 1200) + b'00000000')
        result = ws.receive_json()
        assert result['type'] == 'tracking' and result['quality'] is True
        assert result['frame_id'] == 2
    state = client.portal.call(app.state.sessions.get, session['session_id'])
    assert state['captures'] == []  # Recovery must never enroll or accept a failed take.


def test_session_expiration(env):
    client, app, _ = env
    account, headers = user(client)
    s = client.post('/api/v1/enroll/hand/start', headers=headers, json={'user_id': account['id']}).json()
    state = client.portal.call(app.state.sessions.get, s['session_id'])
    state['created_at'] = time.time() - 700
    # Frequent writes must not extend the absolute session lifetime.
    app.state.sessions.memory[s['session_id']] = (time.time() + 60, state)
    assert client.post('/api/v1/enroll/hand/commit', headers=headers, json={'session_id': s['session_id']}).status_code == 404


def test_delete_revokes_active_websocket_and_transient_samples(env):
    client, app, _ = env
    account, headers = user(client)
    session = client.post('/api/v1/enroll/hand/start', headers=headers, json={'user_id': account['id']}).json()
    sid = session['session_id']
    with client.websocket_connect('/ws/stream/' + sid) as ws:
        ws.send_json({'token': session['session_token']})
        assert ws.receive_json()['type'] == 'ready'
        assert client.delete(f"/api/v1/users/{account['id']}", headers=headers).status_code == 204
        ws.send_bytes(struct.pack('>IQ', 1, 1000) + b'00000000')
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect): ws.receive_json()
    assert client.portal.call(app.state.sessions.get, sid) is None
