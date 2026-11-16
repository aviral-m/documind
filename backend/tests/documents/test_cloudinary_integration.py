import uuid

import pytest

from app.core.config import get_settings
from app.services.storage import CloudinaryStorage, StorageError

pytestmark = pytest.mark.integration


@pytest.fixture
def cloudinary_storage():
    url = get_settings().cloudinary_url
    if not url:
        pytest.skip("CLOUDINARY_URL is not set")
    return CloudinaryStorage(url)


def test_private_pdf_round_trips_through_cloudinary(cloudinary_storage, make_pdf):
    public_id = f"documind/integration-test/{uuid.uuid4()}"
    content = make_pdf(["Cloudinary round trip"])

    cloudinary_storage.save(public_id, content)
    try:
        assert cloudinary_storage.download(public_id) == content
    finally:
        cloudinary_storage.delete(public_id)

    with pytest.raises(StorageError):
        cloudinary_storage.download(public_id)
    cloudinary_storage.delete(public_id)
