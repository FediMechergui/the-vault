import json
import os
from concurrent import futures
import grpc
from contracts import vision_pb2 as pb, vision_pb2_grpc as rpc
from .detector import TrackerPool


class VisionService(rpc.VisionServicer):
    def __init__(self):
        self.pool = TrackerPool(os.getenv("MODEL_DIR", "vision-py/models"))

    def Extract(self, request, context):
        if request.layer not in ("face", "body", "hand") or len(request.jpeg) > 300_000:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid frame")
        try:
            value = self.pool.extract(request.session_id, request.layer, request.jpeg, request.timestamp_ms)
            return pb.Landmarks(json=json.dumps(value, separators=(",", ":")))
        except ValueError as exc:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))

    def Health(self, request, context):
        ready = self.pool.ready()
        return pb.HealthStatus(ready=ready, detail="MediaPipe Tasks CPU" if ready else "Models missing")

    def Release(self, request, context):
        self.pool.release(request.session_id)
        return pb.Empty()


def main():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=6),
                         options=[("grpc.max_receive_message_length", 350_000)])
    rpc.add_VisionServicer_to_server(VisionService(), server)
    server.add_insecure_port(os.getenv("VISION_BIND", "0.0.0.0:50051"))
    server.start()
    print("THE VAULT vision service listening on 50051", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    main()
