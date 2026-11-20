"""G5 Phase 3d: profile photos and the TR-10 upload pipeline (FR-PRO-008; DR-2026-11-19-P3-1)."""

import io
import uuid

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.profiles.models import MatrimonialProfile, ProfilePhoto
from apps.profiles.services.photos import process_photo
from common.providers import EICAR_MARKER

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def private_storage(settings, tmp_path):
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": str(tmp_path)},
        },
    }
    return tmp_path


def make_owner(n=1):
    user = User.objects.create_user(phone_number=f"+92300700{n:04d}", password="Pw-Long-enough-9")
    User.objects.filter(pk=user.pk).update(is_phone_verified=True)
    client = APIClient()
    client.force_authenticate(User.objects.get(pk=user.pk))
    client.post("/api/v1/profiles/")
    return client, MatrimonialProfile.objects.get(owner=user)


def jpeg(size=(400, 300), exif=None, color=(200, 30, 30)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, color).save(out, format="JPEG", exif=exif or b"")
    return out.getvalue()


def png_with_alpha(size=(300, 300)) -> bytes:
    out = io.BytesIO()
    Image.new("RGBA", size, (0, 0, 255, 128)).save(out, format="PNG")
    return out.getvalue()


def gps_exif(orientation=None) -> bytes:
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # Make
    gps = exif.get_ifd(0x8825)
    gps[2] = (31.0, 30.0, 0.0)  # GPSLatitude
    gps[1] = "N"
    if orientation:
        exif[0x0112] = orientation
    return exif.tobytes()


def upload(client, profile, data: bytes, name="photo.jpg", capture=None, **extra):
    file = SimpleUploadedFile(name, data, content_type="image/jpeg")
    url = f"/api/v1/profiles/{profile.id}/photos/"
    if capture is None:
        return client.post(url, {"image": file, **extra}, format="multipart")
    with capture(execute=True):
        return client.post(url, {"image": file, **extra}, format="multipart")


def stored_image(photo: ProfilePhoto) -> Image.Image:
    with default_storage.open(photo.storage_key, "rb") as handle:
        return Image.open(io.BytesIO(handle.read()))


class TestPipeline:
    def test_jpeg_is_reencoded_without_metadata_and_original_discarded(
        self, django_capture_on_commit_callbacks, private_storage
    ):
        client, profile = make_owner()
        response = upload(
            client, profile, jpeg(exif=gps_exif()), capture=django_capture_on_commit_callbacks
        )
        assert response.status_code == 202
        assert "storage_key" not in response.json()
        photo = ProfilePhoto.objects.get()
        assert photo.processing_status == "READY" and photo.is_primary
        assert photo.mime_type == "image/jpeg" and len(photo.checksum) == 64
        assert "://" not in photo.storage_key
        image = stored_image(photo)
        assert dict(image.getexif()) == {} and "exif" not in image.info
        assert not (private_storage / "quarantine").exists() or not any(
            (private_storage / "quarantine").iterdir()
        )

    def test_orientation_is_applied_before_stripping(self, django_capture_on_commit_callbacks):
        client, profile = make_owner()
        upload(
            client,
            profile,
            jpeg(size=(400, 300), exif=gps_exif(orientation=6)),
            capture=django_capture_on_commit_callbacks,
        )
        photo = ProfilePhoto.objects.get()
        assert (photo.width, photo.height) == (300, 400)

    def test_png_with_transparency_becomes_jpeg(self, django_capture_on_commit_callbacks):
        client, profile = make_owner()
        upload(
            client,
            profile,
            png_with_alpha(),
            name="x.png",
            capture=django_capture_on_commit_callbacks,
        )
        photo = ProfilePhoto.objects.get()
        assert photo.processing_status == "READY"
        assert stored_image(photo).format == "JPEG"

    def test_large_images_are_bounded(self, django_capture_on_commit_callbacks, settings):
        settings.PHOTO_MAX_EDGE = 500
        client, profile = make_owner()
        upload(client, profile, jpeg(size=(1600, 1000)), capture=django_capture_on_commit_callbacks)
        photo = ProfilePhoto.objects.get()
        assert max(photo.width, photo.height) == 500

    @pytest.mark.parametrize(
        ("data", "reason"),
        [
            (jpeg() + EICAR_MARKER, "MALWARE_DETECTED"),
            (jpeg(size=(100, 100)), "TOO_SMALL"),
            (b"\xff\xd8\xff\xe0" + b"\x00" * 500, "INVALID_IMAGE"),
        ],
    )
    def test_bad_uploads_are_rejected_and_never_stored(
        self, django_capture_on_commit_callbacks, private_storage, data, reason
    ):
        client, profile = make_owner()
        assert (
            upload(client, profile, data, capture=django_capture_on_commit_callbacks).status_code
            == 202
        )
        photo = ProfilePhoto.objects.get()
        assert (photo.processing_status, photo.rejection_reason) == ("REJECTED", reason)
        assert photo.storage_key is None and not photo.is_primary
        assert not any(p.is_file() for p in private_storage.rglob("*"))

    def test_decompression_bomb_guard(self, django_capture_on_commit_callbacks, settings):
        settings.PHOTO_MAX_PIXELS = 100_000
        client, profile = make_owner()
        upload(client, profile, jpeg(size=(1000, 1000)), capture=django_capture_on_commit_callbacks)
        assert ProfilePhoto.objects.get().rejection_reason == "TOO_LARGE"

    def test_uploads_refused_without_a_scanner(self, settings, private_storage):
        settings.MALWARE_SCANNER = "disabled"
        client, profile = make_owner()
        response = upload(client, profile, jpeg())
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "uploads_unavailable"
        assert not ProfilePhoto.objects.exists()
        assert not any(p.is_file() for p in private_storage.rglob("*"))

    def test_upload_size_limit(self, settings):
        settings.PHOTO_MAX_UPLOAD_BYTES = 1000
        client, profile = make_owner()
        assert upload(client, profile, jpeg()).status_code == 400
        assert not ProfilePhoto.objects.exists()

    def test_processing_is_idempotent(self, django_capture_on_commit_callbacks):
        client, profile = make_owner()
        upload(client, profile, jpeg(), capture=django_capture_on_commit_callbacks)
        photo = ProfilePhoto.objects.get()
        checksum = photo.checksum
        assert process_photo(photo.id) == "skipped"
        photo.refresh_from_db()
        assert photo.checksum == checksum


class TestManagement:
    def test_limit_per_profile(self, django_capture_on_commit_callbacks, settings):
        settings.PHOTO_MAX_PER_PROFILE = 2
        client, profile = make_owner()
        for _ in range(2):
            upload(client, profile, jpeg(), capture=django_capture_on_commit_callbacks)
        response = upload(client, profile, jpeg())
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "photo_limit_reached"

    def test_primary_selection(self, django_capture_on_commit_callbacks):
        client, profile = make_owner()
        upload(client, profile, jpeg(), capture=django_capture_on_commit_callbacks)
        upload(client, profile, jpeg(color=(0, 200, 0)), capture=django_capture_on_commit_callbacks)
        first, second = ProfilePhoto.objects.order_by("uploaded_at")
        assert first.is_primary and not second.is_primary
        url = f"/api/v1/profiles/{profile.id}/photos/{second.id}/"
        assert client.patch(url, {"is_primary": True}, format="json").json()["is_primary"]
        first.refresh_from_db()
        assert not first.is_primary
        upload(client, profile, jpeg() + EICAR_MARKER, capture=django_capture_on_commit_callbacks)
        rejected = ProfilePhoto.objects.get(processing_status="REJECTED")
        bad = client.patch(
            f"/api/v1/profiles/{profile.id}/photos/{rejected.id}/",
            {"is_primary": True},
            format="json",
        )
        assert bad.status_code == 400

    def test_delete_is_soft_and_removes_the_bytes(
        self, django_capture_on_commit_callbacks, private_storage
    ):
        client, profile = make_owner()
        upload(client, profile, jpeg(), capture=django_capture_on_commit_callbacks)
        photo = ProfilePhoto.objects.get()
        with django_capture_on_commit_callbacks(execute=True):
            response = client.delete(f"/api/v1/profiles/{profile.id}/photos/{photo.id}/")
        assert response.status_code == 204
        photo.refresh_from_db()
        assert photo.deleted_at is not None and not photo.is_primary
        assert not default_storage.exists(photo.storage_key)
        assert client.get(f"/api/v1/profiles/{profile.id}/photos/").json() == []

    def test_other_profiles_are_404_everywhere(self, django_capture_on_commit_callbacks):
        owner_client, profile = make_owner(1)
        upload(owner_client, profile, jpeg(), capture=django_capture_on_commit_callbacks)
        photo = ProfilePhoto.objects.get()
        intruder, _ = make_owner(2)
        base = f"/api/v1/profiles/{profile.id}/photos/"
        assert intruder.get(base).status_code == 404
        assert upload(intruder, profile, jpeg()).status_code == 404
        assert (
            intruder.patch(f"{base}{photo.id}/", {"is_primary": False}, format="json").status_code
            == 404
        )
        assert intruder.delete(f"{base}{photo.id}/").status_code == 404
        assert owner_client.delete(f"{base}{uuid.uuid4()}/").status_code == 404
        photo.refresh_from_db()
        assert photo.deleted_at is None and photo.is_primary

    def test_listing_exposes_no_storage_details(self, django_capture_on_commit_callbacks):
        client, profile = make_owner()
        upload(client, profile, jpeg(), capture=django_capture_on_commit_callbacks)
        [item] = client.get(f"/api/v1/profiles/{profile.id}/photos/").json()
        assert "storage_key" not in item and "checksum" not in item
        assert not any("://" in str(v) for v in item.values())


class TestOwnerApprovedLimits:
    """DR-2026-11-20-O-6 photo limits and DR-2026-11-20-O-8 scan outcomes."""

    @pytest.mark.parametrize(
        "data",
        [
            b"%PDF-1.4 not an image at all" * 20,
            b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><script/></svg>' * 5,
            b"GIF89a" + b"\x00" * 500,
            b"not an image" * 50,
        ],
    )
    def test_unsupported_content_is_refused_at_upload_whatever_its_name(
        self, private_storage, data
    ):
        client, profile = make_owner()
        response = upload(client, profile, data, name="innocent.jpg")
        assert response.status_code == 400
        assert not ProfilePhoto.objects.exists()
        assert not any(p.is_file() for p in private_storage.rglob("*"))

    def test_size_limit_is_five_megabytes(self, settings):
        assert settings.PHOTO_MAX_UPLOAD_BYTES == 5 * 1024 * 1024
        client, profile = make_owner()
        big = jpeg() + b"\x00" * (5 * 1024 * 1024)
        assert upload(client, profile, big).status_code == 400

    def test_dimensions_over_4096_are_rejected(self, django_capture_on_commit_callbacks, settings):
        assert settings.PHOTO_MAX_DIMENSION == 4096
        settings.PHOTO_MAX_DIMENSION = 600  # keep the test image small
        client, profile = make_owner()
        upload(client, profile, jpeg(size=(700, 300)), capture=django_capture_on_commit_callbacks)
        photo = ProfilePhoto.objects.get()
        assert (photo.processing_status, photo.rejection_reason) == (
            "REJECTED",
            "DIMENSIONS_TOO_LARGE",
        )

    def test_animated_images_are_rejected(self, django_capture_on_commit_callbacks):
        frames = [Image.new("RGB", (300, 300), c) for c in ((255, 0, 0), (0, 255, 0))]
        out = io.BytesIO()
        frames[0].save(out, format="WEBP", save_all=True, append_images=frames[1:], duration=100)
        client, profile = make_owner()
        upload(client, profile, out.getvalue(), capture=django_capture_on_commit_callbacks)
        photo = ProfilePhoto.objects.get()
        assert photo.rejection_reason == "ANIMATED_IMAGE"

    def test_webp_and_png_are_accepted_and_re_encoded(self, django_capture_on_commit_callbacks):
        client, profile = make_owner()
        out = io.BytesIO()
        Image.new("RGB", (400, 300), (10, 20, 30)).save(out, format="WEBP")
        upload(client, profile, out.getvalue(), capture=django_capture_on_commit_callbacks)
        upload(client, profile, png_with_alpha(), capture=django_capture_on_commit_callbacks)
        for photo in ProfilePhoto.objects.all():
            assert photo.processing_status == "READY" and photo.scan_status == "CLEAN"
            assert photo.mime_type == "image/jpeg" and stored_image(photo).format == "JPEG"

    def test_infected_upload_is_rejected_and_never_stored(
        self, django_capture_on_commit_callbacks, private_storage
    ):
        client, profile = make_owner()
        upload(client, profile, jpeg() + EICAR_MARKER, capture=django_capture_on_commit_callbacks)
        photo = ProfilePhoto.objects.get()
        assert photo.scan_status == "INFECTED" and photo.processing_status == "REJECTED"
        assert photo.storage_key is None
        assert not any(p.is_file() for p in private_storage.rglob("*"))

    def test_unavailable_scanner_is_retried_then_rejected_never_clean(
        self, django_capture_on_commit_callbacks, private_storage, settings
    ):
        from common.providers import MOCK_UNAVAILABLE_MARKER

        settings.PHOTO_SCAN_MAX_ATTEMPTS = 3
        client, profile = make_owner()
        upload(
            client,
            profile,
            jpeg() + MOCK_UNAVAILABLE_MARKER,
            capture=django_capture_on_commit_callbacks,
        )
        photo = ProfilePhoto.objects.get()
        assert photo.scan_status == "FAILED" and photo.scan_attempts == 3
        assert (photo.processing_status, photo.rejection_reason) == ("REJECTED", "SCAN_FAILED")
        assert photo.storage_key is None
        assert not any(p.is_file() for p in private_storage.rglob("*"))

    def test_failed_scan_keeps_the_file_quarantined_between_attempts(self, private_storage):
        from apps.profiles.services.photos import process_photo
        from common.providers import MOCK_UNAVAILABLE_MARKER

        client, profile = make_owner()
        upload(client, profile, jpeg() + MOCK_UNAVAILABLE_MARKER)  # on-commit not run
        photo = ProfilePhoto.objects.get()
        assert photo.scan_status == "PENDING"
        assert process_photo(photo.id) == "retry"
        photo.refresh_from_db()
        assert photo.processing_status == "QUARANTINED" and photo.scan_status == "FAILED"
        assert photo.storage_key is None  # quarantined bytes are never reachable
        assert any(p.is_file() for p in private_storage.rglob("quarantine/*"))

    def test_ready_requires_a_clean_scan_at_the_database(self):
        from django.db import IntegrityError, transaction

        client, profile = make_owner()
        photo = ProfilePhoto.objects.create(profile=profile, uploaded_by=profile.owner)
        with pytest.raises(IntegrityError), transaction.atomic():
            ProfilePhoto.objects.filter(pk=photo.pk).update(
                processing_status="READY",
                storage_key="profile-photos/x.jpg",
                checksum="0" * 64,
                mime_type="image/jpeg",
                size=1,
                width=1,
                height=1,
                scan_status="FAILED",
            )

    def test_one_primary_and_six_photo_limit(self, django_capture_on_commit_callbacks, settings):
        assert settings.PHOTO_MAX_PER_PROFILE == 6
        client, profile = make_owner()
        for i in range(6):
            upload(
                client,
                profile,
                jpeg(color=(i * 30, 0, 0)),
                capture=django_capture_on_commit_callbacks,
            )
        assert upload(client, profile, jpeg()).status_code == 409
        assert ProfilePhoto.objects.filter(is_primary=True).count() == 1
