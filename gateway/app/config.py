from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///.local/vault.db"))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", ""))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", ""))
    encryption_key: str = field(default_factory=lambda: os.getenv("TEMPLATE_KEY", ""))
    admin_key: str = field(default_factory=lambda: os.getenv("ADMIN_KEY", ""))
    vision_address: str = field(default_factory=lambda: os.getenv("VISION_ADDRESS", "localhost:50051"))
    scoring_url: str = field(default_factory=lambda: os.getenv("SCORING_URL", "http://localhost:9910"))
    scoring_token: str = field(default_factory=lambda: os.getenv("SCORING_TOKEN", ""))
    scoring_ca_file: str = field(default_factory=lambda: os.getenv("SCORING_CA_FILE", ""))
    s3_endpoint: str = field(default_factory=lambda: os.getenv("S3_ENDPOINT", ""))
    s3_access_key: str = field(default_factory=lambda: os.getenv("S3_ACCESS_KEY", ""))
    s3_secret_key: str = field(default_factory=lambda: os.getenv("S3_SECRET_KEY", ""))
    bucket: str = "vault-media"
    session_ttl: int = 600

    def validate(self):
        if len(self.jwt_secret) < 32 or len(self.admin_key) < 32:
            raise RuntimeError("Run scripts/bootstrap.py to generate local keys before starting")
        if len(bytes.fromhex(self.encryption_key)) != 32:
            raise RuntimeError("TEMPLATE_KEY must contain 32 random bytes encoded as hex")
        Path(".local").mkdir(exist_ok=True)
