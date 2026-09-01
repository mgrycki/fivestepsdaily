"""Step 3: push the JPEG somewhere with a public URL. IG needs image_url, not an upload."""
import mimetypes
import os

import boto3
from botocore.config import Config as BotoConfig

from . import config


def upload(local_path: str, key: str) -> str:
    client = boto3.client(
        "s3",
        endpoint_url=config.req("S3_ENDPOINT_URL"),
        aws_access_key_id=config.req("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=config.req("S3_SECRET_ACCESS_KEY"),
        region_name=config.S3_REGION,
        config=BotoConfig(signature_version="s3v4"),
    )
    ctype = mimetypes.guess_type(local_path)[0] or "image/jpeg"
    with open(local_path, "rb") as f:
        client.put_object(
            Bucket=config.req("S3_BUCKET"),
            Key=key,
            Body=f,
            ContentType=ctype,
            CacheControl="public, max-age=31536000, immutable",
        )
    base = config.req("PUBLIC_BASE_URL").rstrip("/")
    return f"{base}/{key}"
