import logging
import time
from typing import Protocol
from urllib.parse import urlparse

import cloudinary
import cloudinary.uploader
import cloudinary.utils
import httpx
from cloudinary.exceptions import Error as CloudinaryError

logger = logging.getLogger(__name__)

DOWNLOAD_URL_TTL_SECONDS = 300
DOWNLOAD_TIMEOUT_SECONDS = 60
QUOTA_MESSAGE = "Cloudinary storage quota is used up. Uploads will work again when it resets."
UPLOAD_FAILED_MESSAGE = "This file couldn't be stored. Please try again."
DOWNLOAD_FAILED_MESSAGE = "This file couldn't be retrieved. Please upload it again."


class StorageError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class FileStorage(Protocol):
    def save(self, public_id: str, data: bytes) -> None: ...

    def download(self, public_id: str) -> bytes: ...

    def delete(self, public_id: str) -> None: ...


class CloudinaryStorage:
    """Private raw files on Cloudinary. Only the backend reads them, through signed URLs."""

    def __init__(self, cloudinary_url: str) -> None:
        parsed = urlparse(cloudinary_url)
        if not (parsed.scheme == "cloudinary" and parsed.hostname and parsed.username):
            raise StorageError("CLOUDINARY_URL is missing or malformed.")
        cloudinary.config(
            cloud_name=parsed.hostname,
            api_key=parsed.username,
            api_secret=parsed.password or "",
            secure=True,
        )

    def save(self, public_id: str, data: bytes) -> None:
        try:
            cloudinary.uploader.upload(
                data,
                public_id=public_id,
                resource_type="raw",
                type="private",
                overwrite=False,
            )
        except CloudinaryError as exc:
            logger.exception("Cloudinary upload failed for %s", public_id)
            message = str(exc).lower()
            if "quota" in message or "limit" in message:
                raise StorageError(QUOTA_MESSAGE) from exc
            raise StorageError(UPLOAD_FAILED_MESSAGE) from exc

    def download(self, public_id: str) -> bytes:
        url = cloudinary.utils.private_download_url(
            public_id,
            "",
            resource_type="raw",
            type="private",
            expires_at=int(time.time()) + DOWNLOAD_URL_TTL_SECONDS,
        )
        try:
            response = httpx.get(url, timeout=DOWNLOAD_TIMEOUT_SECONDS)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Cloudinary download failed for %s", public_id)
            raise StorageError(DOWNLOAD_FAILED_MESSAGE) from exc
        return response.content

    def delete(self, public_id: str) -> None:
        try:
            result = cloudinary.uploader.destroy(
                public_id, resource_type="raw", type="private", invalidate=True
            )
        except CloudinaryError as exc:
            raise StorageError(f"Cloudinary could not delete {public_id}.") from exc
        # A file that's already gone is not an error.
        if result.get("result") not in ("ok", "not found"):
            raise StorageError(f"Cloudinary could not delete {public_id}.")
