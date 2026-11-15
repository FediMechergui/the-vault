import json
import ssl
import httpx
import grpc
from contracts import vision_pb2 as pb, vision_pb2_grpc as rpc
from .errors import VisionFailure


class VisionClient:
    def __init__(self, address):
        self.channel = grpc.aio.insecure_channel(address, options=[("grpc.max_receive_message_length", 1024 * 1024)])
        self.stub = rpc.VisionStub(self.channel)

    async def extract(self, sid, layer, jpeg, timestamp):
        # A new session constructs a MediaPipe tracker on its first frame.
        # Leave two seconds for network delivery before the app's 12s deadline.
        try:
            reply = await self.stub.Extract(pb.Frame(session_id=sid, layer=layer, jpeg=jpeg,
                                                    timestamp_ms=timestamp), timeout=10)
        except grpc.RpcError as exc:
            if exc.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                raise VisionFailure('vision_timeout',
                    'Gesture processing on the PC took too long. Retrying the next frame.') from None
            if exc.code() == grpc.StatusCode.INVALID_ARGUMENT:
                raise VisionFailure('vision_frame',
                    'The PC could not process this camera frame. Retrying the next frame.') from None
            raise VisionFailure('vision_unavailable',
                'Gesture tracking on the PC is unavailable. Check its terminal; retrying the next frame.') from None
        return json.loads(reply.json)

    async def health(self):
        reply = await self.stub.Health(pb.Empty(), timeout=2)
        return {"ready": reply.ready, "detail": reply.detail}

    async def release(self, sid):
        try:
            await self.stub.Release(pb.Session(session_id=sid), timeout=2)
        except grpc.RpcError:
            pass

    async def close(self):
        await self.channel.close()


class ScoringClient:
    def __init__(self, url, token="", ca_file=""):
        verify = ssl.create_default_context(cafile=ca_file) if ca_file else True
        self.client = httpx.AsyncClient(base_url=url, timeout=15, verify=verify,
                                       headers={"X-Scoring-Key": token} if token else {})

    async def call(self, operation, layer, **payload):
        reply = await self.client.post(f"/{operation}/{layer}", json=payload)
        if reply.status_code == 422:
            raise ValueError(reply.json().get("detail", "Insufficient capture quality"))
        reply.raise_for_status()
        return reply.json()

    async def health(self):
        reply = await self.client.get("/health", timeout=2)
        reply.raise_for_status()
        return reply.json()

    async def close(self):
        await self.client.aclose()
