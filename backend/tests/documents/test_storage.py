import cloudinary.uploader
import pytest
from cloudinary.exceptions import Error as CloudinaryError

from app.services.storage import QUOTA_MESSAGE, CloudinaryStorage, StorageError


def test_missing_or_malformed_cloudinary_url_is_rejected():
    with pytest.raises(StorageError):
        CloudinaryStorage("")
    with pytest.raises(StorageError):
        CloudinaryStorage("https://example.com/not-cloudinary")


def test_deleting_a_file_that_is_already_gone_is_not_an_error(monkeypatch):
    monkeypatch.setattr(
        cloudinary.uploader, "destroy", lambda *args, **kwargs: {"result": "not found"}
    )
    storage = CloudinaryStorage("cloudinary://key:secret@cloud")

    storage.delete("documind/user/doc")


def test_quota_errors_on_upload_show_the_quota_message(monkeypatch):
    def out_of_credits(*args, **kwargs):
        raise CloudinaryError("Quota exceeded")

    monkeypatch.setattr(cloudinary.uploader, "upload", out_of_credits)
    storage = CloudinaryStorage("cloudinary://key:secret@cloud")

    with pytest.raises(StorageError) as excinfo:
        storage.save("documind/user/doc", b"%PDF-")

    assert excinfo.value.message == QUOTA_MESSAGE
