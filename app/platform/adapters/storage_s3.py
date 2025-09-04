import boto3,os, datetime
from botocore.client import Config
from app.platform.ports.object_storage import ObjectStoragePort
from app.core.config import settings

class S3Storage(ObjectStoragePort):
    def __init__(self):
        session = boto3.session.Session(
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )
        self.s3 = session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = settings.S3_BUCKET

    def presign_upload(self, key: str, content_type: str, expires_seconds: int = 900) -> dict:
        fields = {"Content-Type": content_type}
        conditions = [["starts-with", "$Content-Type", ""], ["content-length-range", 0, 104857600]]
        post = self.s3.generate_presigned_post(
            Bucket=self.bucket,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expires_seconds,
        )
        return {"strategy": "s3-presigned-post", **post}

    def presign_download(self, key: str, expires_seconds: int = 900) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def delete(self, key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=key)

    def presign_post(self, key: str, expires_seconds: int = 600) -> dict:
        s3 = boto3.client("s3", config=Config(signature_version="s3v4"))
        bucket = os.environ.get("S3_BUCKET")
        conditions = [["content-length-range", 0, 104857600]]
        fields = {"acl":"private","Content-Type":"application/octet-stream"}
        url = s3.generate_presigned_post(bucket, key, Fields=fields, Conditions=conditions, ExpiresIn=expires_seconds)
        return url