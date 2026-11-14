from pathlib import Path
import boto3
from botocore.config import Config


class MediaStore:
    def __init__(self, config):
        self.bucket = config.bucket
        self.root = Path("assets")
        self.client = boto3.client("s3", endpoint_url=config.s3_endpoint,
            aws_access_key_id=config.s3_access_key, aws_secret_access_key=config.s3_secret_key,
            region_name="us-east-1", config=Config(signature_version="s3v4")) if config.s3_endpoint else None

    def initialize(self):
        if self.client:
            if self.bucket not in [b["Name"] for b in self.client.list_buckets()["Buckets"]]:
                self.client.create_bucket(Bucket=self.bucket)
            key = "original-meme.png"
            if not self.client.list_objects_v2(Bucket=self.bucket, Prefix=key).get("Contents"):
                self.client.upload_file(str(self.root / key), self.bucket, key)

    def get(self, key):
        if self.client:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        # Key can only be an administrator-selected PNG basename.
        return (self.root / key).read_bytes()

    def put(self, key, content):
        if self.client:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=content, ContentType="image/png")
        else:
            self.root.mkdir(exist_ok=True)
            (self.root / key).write_bytes(content)

    def health(self):
        if self.client:
            self.client.head_bucket(Bucket=self.bucket)
        return {"ready": True, "backend": "minio" if self.client else "local"}
