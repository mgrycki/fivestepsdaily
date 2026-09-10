"""Step 3: give the JPEG a public URL. Instagram needs image_url, it will not take a file.

Default backend is the repo itself: the file is committed under media/ and served from
raw.githubusercontent.com. No bucket, no extra token -- the workflow's own checkout can push.
STORAGE=s3 keeps the R2/S3 path for anyone who wants a real CDN later.
"""
import os
import shutil
import subprocess
import sys

from . import config


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=config.ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def _upload_github(local_path: str, key: str) -> str:
    repo = config.opt("MEDIA_REPO") or _git("remote", "get-url", "origin") \
        .replace("https://github.com/", "").replace("git@github.com:", "").removesuffix(".git")
    branch = config.opt("MEDIA_BRANCH", "main")
    dest = os.path.join(config.ROOT, "media", key)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(local_path, dest)

    _git("add", os.path.relpath(dest, config.ROOT))
    if _git("status", "--porcelain", "--", os.path.relpath(dest, config.ROOT)):
        _git("commit", "-q", "-m", f"media: {key}")
    if config.opt("STORAGE_PUSH", "1") == "1":
        # Meta fetches the URL seconds later, so the push has to land before we return.
        _git("pull", "--rebase", "-q", "origin", branch)
        _git("push", "-q", "origin", f"HEAD:{branch}")
    else:
        print("[storage] STORAGE_PUSH=0, committed locally only", file=sys.stderr)
    return f"https://raw.githubusercontent.com/{repo}/{branch}/media/{key}"


def _upload_s3(local_path: str, key: str) -> str:
    import mimetypes

    import boto3
    from botocore.config import Config as BotoConfig

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
        client.put_object(Bucket=config.req("S3_BUCKET"), Key=key, Body=f, ContentType=ctype,
                          CacheControl="public, max-age=31536000, immutable")
    return f"{config.req('PUBLIC_BASE_URL').rstrip('/')}/{key}"


def upload(local_path: str, key: str) -> str:
    backend = config.opt("STORAGE", "github").lower()
    if backend == "s3":
        return _upload_s3(local_path, key)
    return _upload_github(local_path, key)
