from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import io
import json
import secrets
import struct
import time
import os
from contextlib import asynccontextmanager, suppress
from typing import Literal
import jwt
from fastapi import FastAPI, HTTPException, Depends, Header, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PIL import Image
from sqlalchemy import select, delete, text
from sqlalchemy.exc import IntegrityError

from vault_core.scoring import REPETITIONS, prepare, fuse_scores
from .config import Settings
from .storage import Database, User, Template, Attempt, Setting, VaultItem
from .state import SessionStore, new_state, reset_capture, capture_payload, observe_liveness
from .media import MediaStore

Layer = Literal["face", "body", "hand"]


class CreateUser(BaseModel):
    pseudo: str = Field(min_length=2, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    consent: bool


class Sequence(BaseModel):
    layers: list[Layer] = Field(min_length=1, max_length=3)
    randomized: bool = False


class Start(BaseModel):
    user_id: str


class Commit(BaseModel):
    session_id: str


class AdminSettings(BaseModel):
    minimum_score: float = Field(ge=0.8, le=0.99)


class Meme(BaseModel):
    png_base64: str = Field(max_length=3_000_000)
    caption: str = Field(min_length=1, max_length=200)


def create_app(config=None, vision=None, scorer=None):
    config = config or Settings()
    config.validate()
    database = Database(config)
    sessions = SessionStore(config.redis_url, config.session_ttl)
    media = MediaStore(config)

    @asynccontextmanager
    async def lifespan(app):
        nonlocal vision, scorer
        from .clients import VisionClient, ScoringClient
        vision = vision or VisionClient(config.vision_address)
        scorer = scorer or ScoringClient(config.scoring_url, config.scoring_token, config.scoring_ca_file)
        database.initialize()
        await asyncio.to_thread(media.initialize)

        async def maintenance():
            while True:
                await asyncio.sleep(60)
                await sessions.sweep()
                with database.session.begin() as db:
                    db.execute(delete(Attempt).where(Attempt.started_at < time.time() - 30 * 86400))

        task = asyncio.create_task(maintenance())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await sessions.close()
            await vision.close()
            await scorer.close()
            database.engine.dispose()

    app = FastAPI(title="THE VAULT", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware,
        allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080").split(","),
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Session-Token"])
    app.state.database, app.state.sessions = database, sessions

    def token(uid, scope, lifetime):
        return jwt.encode({"sub": uid, "scope": scope, "iss": "the-vault", "aud": "vault-app",
                           "iat": int(time.time()), "exp": int(time.time()) + lifetime,
                           "jti": secrets.token_hex(12)}, config.jwt_secret, algorithm="HS256")

    def verify(value, scope):
        try:
            claims = jwt.decode(value, config.jwt_secret, algorithms=["HS256"], audience="vault-app",
                                issuer="the-vault", options={"require": ["sub", "scope", "exp", "iat"]})
            if claims["scope"] != scope:
                raise ValueError()
            with database.session() as db:
                if not db.get(User, claims["sub"]):
                    raise ValueError()
            return claims["sub"]
        except (jwt.PyJWTError, ValueError):
            raise HTTPException(401, "Invalid or expired credential") from None

    def management(authorization: str = Header(default="")):
        return verify(authorization.removeprefix("Bearer "), "manage")

    def unlocked(authorization: str = Header(default="")):
        return verify(authorization.removeprefix("Bearer "), "vault")

    def admin(x_admin_key: str = Header(default="")):
        if not hmac.compare_digest(x_admin_key, config.admin_key):
            raise HTTPException(401, "Administrator credential required")

    async def limited(request, key, count=20):
        host = request.client.host if request.client else "local"
        if not await sessions.rate_limit(f"{key}:{host}", count):
            raise HTTPException(429, "Too many requests; try again in a minute")

    async def session_owned(sid, secret):
        state = await sessions.get(sid)
        if not state or not hmac.compare_digest(state["secret"], secret):
            raise HTTPException(401, "Session expired or invalid")
        with database.session() as db:
            user = db.get(User, state["user_id"])
            if not user:
                raise HTTPException(401, "Account no longer exists")
            if state["kind"] == "auth" and user.locked_until > time.time():
                raise HTTPException(423, "Vault locked for five minutes")
        return state

    async def invalidate_user(uid):
        for sid in await sessions.delete_user(uid):
            await vision.release(sid)

    async def save_active_state(state):
        # Serialize against deletion/configuration/auth restart. A slow vision call
        # must never recreate a revoked session after the deletion endpoint returns.
        async with sessions.lock(f"user:{state['user_id']}"):
            await session_owned(state["id"], state["secret"])
            await sessions.put(state["id"], state)

    def challenge(state):
        layer = state["layers"][state["index"]]
        return {"layer": layer, "step": state["index"] + 1, "total": len(state["layers"]),
                "duration_ms": {"face": 3800, "body": 5000, "hand": 8000}[layer],
                "liveness": state["live_challenge"] if layer == "face" and not state["live_done"] else None,
                "repetition": len(state["captures"]) + 1,
                "repetitions": REPETITIONS[layer] if state["kind"] == "enroll" else 1}

    @app.post("/api/v1/users", status_code=201)
    async def create_user(body: CreateUser, request: Request):
        await limited(request, "signup", 10)
        if not body.consent:
            raise HTTPException(422, "Explicit consent is required before camera capture")
        try:
            with database.session.begin() as db:
                user = User(pseudo=body.pseudo)
                db.add(user)
                db.flush()
                uid = user.id
        except IntegrityError:
            raise HTTPException(409, "This pseudonym is already in use") from None
        return {"id": uid, "pseudo": body.pseudo, "management_token": token(uid, "manage", 365 * 86400)}

    @app.get("/api/v1/users/me")
    async def profile(uid=Depends(management)):
        with database.session() as db:
            user = db.get(User, uid)
            layers = list(db.scalars(select(Template.layer).where(Template.user_id == uid)))
            return {"id": uid, "pseudo": user.pseudo, "sequence": user.sequence,
                    "randomized": bool(user.randomized), "enrolled": layers, "locked_until": user.locked_until}

    @app.put("/api/v1/users/{uid}/sequence")
    async def sequence(uid: str, body: Sequence, owner=Depends(management)):
        if uid != owner:
            raise HTTPException(403, "This is not your vault")
        if len(set(body.layers)) != len(body.layers) or body.randomized and len(body.layers) != 3:
            raise HTTPException(422, "Choose distinct layers; randomized mode requires all three")
        async with sessions.lock(f"user:{uid}"):
            with database.session.begin() as db:
                user = db.get(User, uid)
                user.sequence, user.randomized = body.layers, int(body.randomized)
            await invalidate_user(uid)
        return {"layers": body.layers, "randomized": body.randomized}

    @app.post("/api/v1/enroll/{layer}/start")
    async def enroll_start(layer: Layer, body: Start, owner=Depends(management)):
        if body.user_id != owner:
            raise HTTPException(403, "This is not your vault")
        if not await sessions.rate_limit(f"enroll:{owner}", 15):
            raise HTTPException(429, "Too many enrollment sessions")
        state = new_state(owner, "enroll", [layer])
        async with sessions.lock(f"user:{owner}"):
            with database.session() as db:
                if not db.get(User, owner):
                    raise HTTPException(401, "Account no longer exists")
            await sessions.put(state["id"], state)
        return {"session_id": state["id"], "session_token": state["secret"], "challenge": challenge(state)}

    @app.post("/api/v1/enroll/{layer}/commit")
    async def enroll_commit(layer: Layer, body: Commit, owner=Depends(management)):
        async with sessions.lock(body.session_id):
            state = await sessions.get(body.session_id)
            if not state or state["user_id"] != owner or state["kind"] != "enroll" or state["layers"] != [layer]:
                raise HTTPException(404, "Enrollment not found")
            if len(state["captures"]) != REPETITIONS[layer]:
                raise HTTPException(422, "Complete all repetitions first")
            try:
                result = await scorer.call("enroll", layer, captures=state["captures"])
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
            except Exception:
                raise HTTPException(503, "Scoring engine unavailable; retry shortly") from None
            async with sessions.lock(f"user:{owner}"):
                with database.session.begin() as db:
                    if not db.get(User, owner):
                        raise HTTPException(404, "Account no longer exists")
                    existing = db.get(Template, (owner, layer))
                    encrypted = database.encrypt(owner, layer, result["template"])
                    if existing:
                        existing.features, existing.updated_at = encrypted, time.time()
                    else:
                        db.add(Template(user_id=owner, layer=layer, features=encrypted))
                await invalidate_user(owner)
            await vision.release(state["id"])
            return {"enrolled": layer, "engine": result["engine"],
                    "consistency": max(0, 1 - result["template"]["mu"])}

    @app.post("/api/v1/auth/start")
    async def auth_start(body: Start, request: Request):
        await limited(request, "auth", 30)
        async with sessions.lock(f"user:{body.user_id}"):
            with database.session.begin() as db:
                user = db.get(User, body.user_id)
                if not user:
                    raise HTTPException(404, "Vault not found")
                if user.locked_until > time.time():
                    raise HTTPException(423, {"message": "Vault locked", "retry_after": int(user.locked_until - time.time()) + 1})
                if user.locked_until:
                    user.failures, user.locked_until = 0, 0
                layers = list(user.sequence)
                enrolled = list(db.scalars(select(Template.layer).where(Template.user_id == user.id)))
                if any(layer not in enrolled for layer in layers):
                    raise HTTPException(409, "Enroll every selected layer first")
                if user.randomized:
                    secrets.SystemRandom().shuffle(layers)
                state = new_state(user.id, "auth", layers)
                if user.randomized:
                    state["layers"].append(secrets.choice(layers))
            # Only one active authentication per account; new starts cannot bypass lockout.
            await invalidate_user(body.user_id)
            await sessions.put(state["id"], state)
        return {"session_id": state["id"], "session_token": state["secret"], "challenge": challenge(state)}

    @app.post("/api/v1/auth/{sid}/next")
    async def auth_next(sid: str, x_session_token: str = Header(default="")):
        async with sessions.lock(sid):
            state = await session_owned(sid, x_session_token)
            if state["kind"] != "auth" or state["status"] != "captured" or len(state["captures"]) != 1:
                raise HTTPException(409, "Finish the current capture first")
            layer = state["layers"][state["index"]]
            if layer == "face" and not state["live_done"]:
                raise HTTPException(409, "Complete the liveness challenge first")
            with database.session() as db:
                template = database.decrypt(db.get(Template, (state["user_id"], layer)))
                minimum_score = db.get(Setting, "minimum_score").value
            try:
                result = await scorer.call("score", layer, capture=state["captures"][0],
                                           template=template, minimum_score=minimum_score)
            except ValueError as exc:
                state["captures"] = []
                reset_capture(state)
                await save_active_state(state)
                raise HTTPException(422, str(exc)) from None
            except Exception:
                raise HTTPException(503, "Scoring engine unavailable; retry shortly") from None
            state["results"].append({"layer": layer, **result})
            terminal = not result["passed"] or state["index"] == len(state["layers"]) - 1
            if terminal:
                async with sessions.lock(f"user:{state['user_id']}"):
                    # Re-read after scoring so deletion, lockout or a new login invalidates this result.
                    await session_owned(sid, x_session_token)
                    with database.session.begin() as db:
                        user = db.get(User, state["user_id"])
                        user.failures = 0 if result["passed"] else user.failures + 1
                        if user.failures >= 3:
                            user.locked_until = time.time() + 300
                        db.add(Attempt(user_id=user.id, started_at=state["created_at"], layers=state["layers"],
                                       scores=state["results"], result="success" if result["passed"] else "failed",
                                       latency_ms=(time.time() - state["created_at"]) * 1000))
                        locked_until = user.locked_until
                    await sessions.delete(sid)
                await vision.release(sid)
                if result["passed"]:
                    return {"status": "unlocked", "result": result, "fusion": fuse_scores(state["results"]),
                            "access_token": token(state["user_id"], "vault", 900), "expires_in": 900}
                return {"status": "failed", "result": result, "locked_until": locked_until}
            state["index"] += 1
            state["captures"] = []
            state["live_done"] = False
            state["live_count"], state["live_closed"], state["live_centered"] = 0, False, False
            state["live_challenge"] = secrets.choice(["blink_twice", "turn_left", "turn_right"])
            reset_capture(state)
            # Avoid resurrecting invalidated sessions.
            await session_owned(sid, x_session_token)
            await save_active_state(state)
            return {"status": "next", "result": result, "challenge": challenge(state)}

    @app.websocket("/ws/stream/{sid}")
    async def stream(ws: WebSocket, sid: str):
        await ws.accept()
        try:
            hello = await asyncio.wait_for(ws.receive_json(), timeout=5)
            secret = str(hello.get("token", ""))
            state = await session_owned(sid, secret)
            await ws.send_json({"type": "ready", "challenge": challenge(state)})
            while True:
                message = await asyncio.wait_for(ws.receive(), timeout=25)
                if message["type"] == "websocket.disconnect":
                    break
                async with sessions.lock(sid):
                    state = await session_owned(sid, secret)
                    layer = state["layers"][state["index"]]
                    if message.get("text") is not None:
                        event = json.loads(message["text"])
                        if event.get("type") == "begin":
                            needed = REPETITIONS[layer] if state["kind"] == "enroll" else 1
                            if len(state["captures"]) >= needed or state["status"] != "ready":
                                await ws.send_json({"type": "error", "message": "Capture is already complete or running"})
                                continue
                            if layer == "face" and not state["live_done"]:
                                await ws.send_json({"type": "error", "message": "Complete the liveness prompt first"})
                                continue
                            reset_capture(state)
                            state.update(status="capturing", capture_started=time.monotonic())
                            await ws.send_json({"type": "capturing"})
                        elif event.get("type") == "finish":
                            if state["status"] != "capturing":
                                continue
                            try:
                                if layer == "hand" and not state["trace_done"]:
                                    raise ValueError("Pinch again to finish your signature")
                                payload = capture_payload(state["frames"])
                                prepare(layer, payload)
                                state["captures"].append(payload)
                                reset_capture(state)
                                needed = REPETITIONS[layer] if state["kind"] == "enroll" else 1
                                if len(state["captures"]) == needed:
                                    state["status"] = "captured"
                                await ws.send_json({"type": "captured", "completed": len(state["captures"]),
                                                    "required": needed, "ready_to_commit": state["status"] == "captured"})
                            except (ValueError, KeyError, IndexError) as exc:
                                reset_capture(state)
                                await ws.send_json({"type": "quality_error", "message": str(exc)})
                        await save_active_state(state)
                        continue
                    blob = message.get("bytes", b"")
                    if not 16 < len(blob) <= 300_000:
                        await ws.close(code=1009)
                        break
                    frame_id, timestamp = struct.unpack(">IQ", blob[:12])
                    if frame_id <= state["last_frame"] or timestamp <= state["last_timestamp"]:
                        await ws.send_json({"type": "error", "message": "Duplicate or out-of-order frame"})
                        continue
                    if not await sessions.rate_limit(f"frames:{sid}", 22, 1):
                        await ws.send_json({"type": "dropped", "frame_id": frame_id})
                        continue
                    state["last_frame"], state["last_timestamp"] = frame_id, timestamp
                    started = time.perf_counter()
                    try:
                        data = await vision.extract(sid, layer, blob[12:], timestamp)
                    except Exception:
                        await ws.send_json({"type": "error", "message": "Vision service unavailable"})
                        continue
                    del blob
                    if data.get("quality", False):
                        if layer == "face" and not state["live_done"]:
                            state["live_done"] = observe_liveness(state, data)
                        if state["status"] == "capturing" and len(state["frames"]) < 180:
                            if time.monotonic() - state["capture_started"] > 12:
                                reset_capture(state)
                                await ws.send_json({"type": "quality_error", "message": "Capture timed out; try again"})
                            else:
                                keep = True
                                if layer == "hand":
                                    pinched = data.get("pinch", False)
                                    if not pinched:
                                        state["pinch_released"] = True
                                    rising = pinched and not state["pinch_down"] and state["pinch_released"]
                                    if rising and not state["trace_done"]:
                                        if state["drawing"] and len(state["frames"]) >= 8:
                                            state["drawing"], state["trace_done"] = False, True
                                        elif not state["drawing"]:
                                            state["drawing"] = True
                                    state["pinch_down"] = pinched
                                    keep = state["drawing"] and not pinched
                                if keep:
                                    sample = {"timestamp_ms": timestamp, "features": data["features"]}
                                    if layer == "face":
                                        sample["geometry"] = data["geometry"]
                                    state["frames"].append(sample)
                    # Landmarks are live output only. Frame bytes are never persisted.
                    await save_active_state(state)
                    await ws.send_json({"type": "tracking", "frame_id": frame_id,
                        "timestamp_ms": timestamp, "quality": data.get("quality", False),
                        "message": data.get("message", ""), "landmarks": data.get("landmarks", []),
                        "gesture": data.get("gesture", ""), "pinch": data.get("pinch", False),
                        "drawing": state["drawing"], "trace_done": state["trace_done"],
                        "liveness_passed": state["live_done"], "samples": len(state["frames"]),
                        "latency_ms": round((time.perf_counter() - started) * 1000, 1)})
        except WebSocketDisconnect:
            pass
        except (HTTPException, asyncio.TimeoutError, ValueError, KeyError, TypeError):
            with suppress(RuntimeError, WebSocketDisconnect):
                await ws.close(code=1008)
        finally:
            await vision.release(sid)

    @app.get("/api/v1/vault")
    async def vault(uid=Depends(unlocked)):
        with database.session() as db:
            item = db.get(VaultItem, "active")
            caption = item.caption
        media_token = token(uid, "media", 120)
        return {"caption": caption, "meme_url": f"/api/v1/vault/meme?ticket={media_token}",
                "transparency": {"fictional": True, "partners": 347,
                    "categories": [{"label": "Location", "count": 128}, {"label": "Shopping habits", "count": 96},
                                   {"label": "Interests", "count": 82}, {"label": "Contacts", "count": 41}],
                    "notice": "Satire. All counters are invented. THE VAULT does not collect or share these categories.",
                    "learn_url": "https://www.cnil.fr/fr/maitriser-mes-donnees"}}

    @app.get("/api/v1/vault/meme")
    async def meme(ticket: str):
        verify(ticket, "media")
        with database.session() as db:
            item = db.get(VaultItem, "active")
            content = await asyncio.to_thread(media.get, item.object_key)
        return Response(content, media_type="image/png", headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})

    @app.delete("/api/v1/users/{uid}", status_code=204)
    async def delete_user(uid: str, owner=Depends(management)):
        if uid != owner:
            raise HTTPException(403, "This is not your vault")
        async with sessions.lock(f"user:{uid}"):
            with database.session.begin() as db:
                db.execute(delete(Attempt).where(Attempt.user_id == uid))
                db.execute(delete(Template).where(Template.user_id == uid))
                db.execute(delete(User).where(User.id == uid))
            await invalidate_user(uid)
        return Response(status_code=204)

    @app.get("/api/v1/health")
    async def health():
        async def probe(call):
            try:
                return await call()
            except Exception:
                return {"ready": False, "detail": "unavailable"}
        checks = dict(zip(["vision", "scoring"], await asyncio.gather(probe(vision.health), probe(scorer.health))))
        try:
            with database.session() as db:
                db.execute(text("SELECT 1"))
            checks["database"] = {"ready": True}
        except Exception:
            checks["database"] = {"ready": False}
        try:
            if sessions.redis:
                await sessions.redis.ping()
            checks["sessions"] = {"ready": True, "backend": "redis" if sessions.redis else "memory"}
        except Exception:
            checks["sessions"] = {"ready": False}
        try:
            checks["media"] = await asyncio.to_thread(media.health)
        except Exception:
            checks["media"] = {"ready": False}
        ready = all(c.get("ready", False) for c in checks.values())
        return Response(json.dumps({"ready": ready, "services": checks}), status_code=200 if ready else 503,
                        media_type="application/json")

    @app.get("/api/v1/admin/settings", dependencies=[Depends(admin)])
    async def get_settings():
        with database.session() as db:
            return {s.key: s.value for s in db.scalars(select(Setting))}

    @app.put("/api/v1/admin/settings", dependencies=[Depends(admin)])
    async def set_settings(body: AdminSettings):
        with database.session.begin() as db:
            db.get(Setting, "minimum_score").value = body.minimum_score
        return body

    @app.get("/api/v1/admin/attempts", dependencies=[Depends(admin)])
    async def attempts():
        with database.session() as db:
            return [{"id": a.id, "user_id": a.user_id, "result": a.result, "scores": a.scores,
                     "started_at": a.started_at, "latency_ms": a.latency_ms}
                    for a in db.scalars(select(Attempt).order_by(Attempt.started_at.desc()).limit(100))]

    @app.delete("/api/v1/admin/attempts", dependencies=[Depends(admin)], status_code=204)
    async def purge_attempts():
        with database.session.begin() as db:
            db.execute(delete(Attempt))
        return Response(status_code=204)

    @app.put("/api/v1/admin/meme", dependencies=[Depends(admin)])
    async def set_meme(body: Meme):
        try:
            raw = base64.b64decode(body.png_base64, validate=True)
            image = Image.open(io.BytesIO(raw))
            if image.format != "PNG" or max(image.size) > 2048:
                raise ValueError()
            image.verify()
        except Exception:
            raise HTTPException(422, "Supply a valid PNG up to 2048 pixels") from None
        await asyncio.to_thread(media.put, "custom-meme.png", raw)
        with database.session.begin() as db:
            item = db.get(VaultItem, "active")
            item.object_key, item.caption = "custom-meme.png", body.caption
        return {"updated": True}

    return app
