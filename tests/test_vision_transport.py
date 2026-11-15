import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

import grpc
import pytest
from contracts import vision_pb2 as pb, vision_pb2_grpc as rpc
from gateway.app.clients import VisionClient
from gateway.app.errors import VisionFailure


@pytest.mark.parametrize('mode', ['slow_start', 'invalid_frame', 'unavailable'])
def test_real_rpc_slow_start_and_safe_errors(mode):
    class TestVision(rpc.VisionServicer):
        def Extract(self, request, context):
            if mode == 'slow_start':
                time.sleep(4.1)  # Exceeds both original 3s RPC and 4s app deadlines.
                return pb.Landmarks(json='{"quality": false, "landmarks": []}')
            code = grpc.StatusCode.INVALID_ARGUMENT if mode == 'invalid_frame' else grpc.StatusCode.UNAVAILABLE
            context.abort(code, 'internal test detail must not reach the app')

    server = grpc.server(ThreadPoolExecutor(max_workers=1))
    rpc.add_VisionServicer_to_server(TestVision(), server)
    port = server.add_insecure_port('127.0.0.1:0')
    server.start()

    async def exercise():
        client = VisionClient(f'127.0.0.1:{port}')
        try:
            if mode == 'slow_start':
                result = await client.extract('test', 'hand', b'test-frame', 1000)
                assert result == {'quality': False, 'landmarks': []}
            else:
                with pytest.raises(VisionFailure) as error:
                    await client.extract('test', 'hand', b'test-frame', 1000)
                assert error.value.code == ('vision_frame' if mode == 'invalid_frame' else 'vision_unavailable')
                assert error.value.retryable
                assert 'internal test detail' not in str(error.value)
        finally:
            await client.close()

    try:
        asyncio.run(exercise())
    finally:
        server.stop(0).wait()
