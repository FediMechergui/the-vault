import pytest
from gateway.app.storage import Template
from vault_core.scoring import enroll, REPETITIONS
from .test_gateway import env, user, insert_capture
from .samples import capture


def test_full_sequence_cannot_skip_face_liveness_or_order(env):
    client, app, _ = env
    account, headers = user(client)
    with app.state.database.session.begin() as db:
        for layer in ['face', 'body', 'hand']:
            template = enroll(layer, [capture(layer, i) for i in range(REPETITIONS[layer])])
            db.add(Template(user_id=account['id'], layer=layer,
                features=app.state.database.encrypt(account['id'], layer, template)))
    session = client.post('/api/v1/auth/start', json={'user_id': account['id']}).json()
    sid, secret = session['session_id'], session['session_token']
    assert session['challenge']['layer'] == 'face'
    insert_capture(client, app, sid, 'face', 1)
    assert client.post(f'/api/v1/auth/{sid}/next', headers={'X-Session-Token': secret}).status_code == 409
    state = client.portal.call(app.state.sessions.get, sid)
    state['live_done'] = True  # Controlled test fixture, not a public API.
    client.portal.call(app.state.sessions.put, sid, state)
    for layer, expected in [('face', 'body'), ('body', 'hand'), ('hand', None)]:
        if layer != 'face': insert_capture(client, app, sid, layer, 1)
        reply = client.post(f'/api/v1/auth/{sid}/next', headers={'X-Session-Token': secret})
        assert reply.status_code == 200, reply.text
        if expected:
            assert reply.json()['challenge']['layer'] == expected
            assert 'access_token' not in reply.json()
        else:
            assert reply.json()['status'] == 'unlocked'
            assert reply.json()['fusion']['passed']
