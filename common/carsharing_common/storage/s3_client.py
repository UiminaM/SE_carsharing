
from __future__ import annotations

import asyncio
from typing import Any

import boto3
import structlog
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

logger: structlog.stdlib.BoundLogger = structlog.get_logger()

class S3Client:

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        signature_version: str = "s3v4",
    ) -> None:
        self._endpoint_url = endpoint_url
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=BotoConfig(signature_version=signature_version),
        )

    async def ensure_bucket(self, bucket: str) -> None:

        def _ensure() -> None:
            try:
                self._client.head_bucket(Bucket=bucket)
                return
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if code not in ("404", "NoSuchBucket", "NotFound"):
                    raise
            self._client.create_bucket(Bucket=bucket)

        await asyncio.to_thread(_ensure)
        logger.info("s3_bucket_ready", bucket=bucket, endpoint=self._endpoint_url)

    async def put_object(
        self,
        bucket: str,
        key: str,
        body: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> None:
        def _put() -> None:
            self._client.put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
                Metadata=metadata or {},
            )

        await asyncio.to_thread(_put)
        logger.info(
            "s3_object_uploaded",
            bucket=bucket,
            key=key,
            size=len(body),
        )

    async def get_object(self, bucket: str, key: str) -> bytes:
        def _get() -> bytes:
            resp = self._client.get_object(Bucket=bucket, Key=key)
            return resp["Body"].read()

        return await asyncio.to_thread(_get)

    async def object_exists(self, bucket: str, key: str) -> bool:
        def _head() -> bool:
            try:
                self._client.head_object(Bucket=bucket, Key=key)
                return True
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if code in ("404", "NoSuchKey", "NotFound"):
                    return False
                raise

        return await asyncio.to_thread(_head)
