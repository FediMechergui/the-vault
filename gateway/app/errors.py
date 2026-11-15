class VisionFailure(RuntimeError):
    """A public capture error without frame data or internal RPC details."""
    def __init__(self, code, message, retryable=True):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
