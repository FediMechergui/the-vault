from __future__ import annotations

import asyncio
import copy
import json
import secrets
import time
from contextlib import asynccontextmanager
from redis.asyncio import Redis


class SessionStore:
    """Ephemeral landmarks only. Redis persistence is disabled in Compose."""
    def __init__(self, url="", ttl=600):
        self.redis = Redis.from_url(url, decode_responses=True) if url else None
        self.ttl = ttl
        self.memory = {}
        self.locks = {}
        self.rates = {}

    async def get(self, key):
        if self.redis:
            value = await self.redis.get(f"session:{key}")
            state = json.loads(value) if value else None
            if state and state["created_at"] + self.ttl <= time.time():
                await self.delete(key)
                return None
            return state
        entry = self.memory.get(key)
        if entry and entry[0] > time.time() and entry[1]["created_at"] + self.ttl > time.time():
            return copy.deepcopy(entry[1])
        self.memory.pop(key, None)
        return None

    async def put(self, key, value):
        remaining = max(1, int(value.get("created_at", time.time()) + self.ttl - time.time()))
        if self.redis:
            await self.redis.set(f"session:{key}", json.dumps(value), ex=remaining)
        else:
            self.memory[key] = (time.time() + remaining, copy.deepcopy(value))

    async def delete(self, key):
        if self.redis:
            await self.redis.delete(f"session:{key}")
        self.memory.pop(key, None)

    async def delete_user(self, user_id):
        deleted = []
        keys = [k async for k in self.redis.scan_iter("session:*")] if self.redis else list(self.memory)
        for key in keys:
            sid = key.removeprefix("session:") if self.redis else key
            state = await self.get(sid)
            if state and state["user_id"] == user_id:
                await self.delete(sid)
                deleted.append(sid)
        return deleted

    async def rate_limit(self, key, count=30, seconds=60):
        if self.redis:
            name = f"rate:{key}:{int(time.time()) // seconds}"
            value = await self.redis.incr(name)
            if value == 1:
                await self.redis.expire(name, seconds)
            return value <= count
        now = time.time()
        self.rates = {k: v for k, v in self.rates.items() if v[0] > now}
        expires, value = self.rates.get(key, (now + seconds, 0))
        self.rates[key] = (expires, value + 1)
        return value < count

    @asynccontextmanager
    async def lock(self, key):
        if self.redis:
            lock = self.redis.lock(f"lock:{key}", timeout=30, blocking_timeout=5)
            if not await lock.acquire():
                raise TimeoutError("Session is busy")
            try:
                yield
            finally:
                await lock.release()
        else:
            lock = self.locks.setdefault(key, asyncio.Lock())
            async with lock:
                yield

    async def sweep(self):
        if not self.redis:
            expired = [k for k, v in self.memory.items() if v[0] <= time.time()]
            for key in expired:
                self.memory.pop(key, None)
                self.locks.pop(key, None)

    async def close(self):
        if self.redis:
            await self.redis.aclose()


def new_state(user_id, kind, layers, ttl=600):
    return {"id": secrets.token_urlsafe(24), "secret": secrets.token_urlsafe(32),
            "created_at": time.time(), "user_id": user_id, "kind": kind, "layers": layers,
            "index": 0, "results": [], "captures": [], "frames": [], "status": "ready",
            "last_frame": -1, "last_timestamp": -1, "capture_started": 0,
            "live_challenge": secrets.choice(["blink_twice", "turn_left", "turn_right"]),
            "live_count": 0, "live_closed": False, "live_centered": False,
            "live_done": kind == "enroll", "pinch_down": False, "pinch_released": False,
            "drawing": False, "trace_done": False}


def reset_capture(state):
    state.update(frames=[], status="ready", capture_started=0, pinch_down=False,
                 pinch_released=False, drawing=False, trace_done=False)


def capture_payload(frames):
    result = {"times": [f["timestamp_ms"] for f in frames], "values": [f["features"] for f in frames]}
    if frames and "geometry" in frames[0]:
        result["geometry"] = [f["geometry"] for f in frames]
    return result


def observe_liveness(state, data):
    # Reject flat/missing topology. This is basic liveness, not anti-replay certification.
    if not data.get("depth_ok", False):
        return False
    challenge = state["live_challenge"]
    if challenge == "blink_twice":
        blink = data.get("blink", 0)
        if blink > 0.55:
            state["live_closed"] = True
        elif blink < 0.25 and state["live_closed"]:
            state["live_count"] += 1
            state["live_closed"] = False
        return state["live_count"] >= 2
    yaw = data.get("yaw", 0)
    if abs(yaw) < 0.12:
        state["live_centered"] = True
    return state["live_centered"] and (yaw < -0.22 if challenge == "turn_left" else yaw > 0.22)
