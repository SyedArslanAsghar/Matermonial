"""Profile photos and the upload pipeline (FR-PRO-008, FR-017; TR-10, DR-2026-11-19-P3-1).

Pipeline (TR-10): quarantine → byte-level type detection → malware scan → decode, verify and
re-encode (EXIF/GPS and every other metadata stripped, orientation applied, size bounded) →
store the re-encoded image only → discard the original.

- Uploads are refused up front (503 ``uploads_unavailable``) when no scanner is available, so
  nothing is ever accepted unscanned. Deployed settings refuse the mock scanner.
- Only JPEG, PNG and WebP are accepted, judged by their bytes, never by name or header. HEIC
  needs a separately approved decoder. Output is always JPEG.
- Processing runs in a Celery task after commit (CC-R53). It is idempotent: only a QUARANTINED,
  live row is processed. The image work happens outside any database transaction.
- Storage is private (``default_storage``, never served by Django; CC-R46). Keys are
  ``quarantine/<photo>`` and ``profile-photos/<profile>/<photo>.jpg`` (per-group prefixes).
  No URL is stored or returned; controlled delivery to viewers is Module 10 (Phase 6).
- Deleting is soft: the row stays (FR-017) and the stored bytes are removed after commit.
- Lock order: User FOR SHARE → profile FOR UPDATE → photo rows.
"""

import hashlib
import io
import logging

import filetype
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageOps
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.accounts.models import User
from apps.accounts.services.pseudonyms import pseudonym_for
from apps.audit.services import record_audit
from common.db.locking import LockLevel, lock_plan, lock_rows_for_share, lock_rows_for_update
from common.providers import DisabledScanner, ProviderDisabledError, get_malware_scanner

from .. import reference
from ..models import MatrimonialProfile, ProfilePhoto
from .profiles import InvalidProfileState

logger = logging.getLogger(__name__)
ACCEPTED_MIME = {"image/jpeg", "image/png", "image/webp"}
OUTPUT_MIME = "image/jpeg"


class UploadsUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "uploads_unavailable"
    default_detail = "Photo uploads are not available right now."


class PhotoLimitReached(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "photo_limit_reached"
    default_detail = "This profile already has the maximum number of photos."


def _quarantine_key(photo) -> str:
    return f"quarantine/{photo.id}"


def _final_key(photo) -> str:
    return f"profile-photos/{photo.profile_id}/{photo.id}.jpg"


def _audit(user, profile, action, **metadata):
    record_audit(
        action=action,
        resource_type="profiles.photo",
        actor_type="USER",
        result="SUCCESS",
        category="STATE_CHANGE",
        actor_user_id=user.pk,
        subject_user_id=profile.owner_id,
        represented_profile_pseudonym=pseudonym_for("PROFILE", profile.id),
        metadata=metadata,
    )


def _lock_own_profile(user, profile_id) -> MatrimonialProfile:
    lock_rows_for_share(User.objects.filter(pk=user.pk), LockLevel.ACCOUNT)
    locked = lock_rows_for_update(
        MatrimonialProfile.objects.filter(pk=profile_id, owner_id=user.pk),
        LockLevel.PROFILE,
        anchor=True,
    )
    if not locked:
        raise NotFound()
    profile = locked[0]
    if profile.profile_status == MatrimonialProfile.Status.CLOSED:
        raise InvalidProfileState()
    return profile


def live_photos(profile_id):
    return ProfilePhoto.objects.filter(profile_id=profile_id, deleted_at__isnull=True)


# --- Upload --------------------------------------------------------------------------------


def upload_photo(user: User, profile_id, upload, photo_type: str | None) -> ProfilePhoto:
    if isinstance(get_malware_scanner(), DisabledScanner):
        raise UploadsUnavailable()
    if photo_type is not None and not reference.is_allowed("photo_type", photo_type):
        raise ValidationError({"photo_type": [reference.choice_error("photo_type")]})
    if upload.size > settings.PHOTO_MAX_UPLOAD_BYTES:
        raise ValidationError({"image": ["The file is too large."]})
    data = upload.read(settings.PHOTO_MAX_UPLOAD_BYTES + 1)
    if len(data) > settings.PHOTO_MAX_UPLOAD_BYTES:
        raise ValidationError({"image": ["The file is too large."]})

    stored_key = None
    try:
        with (
            transaction.atomic(),
            lock_plan(
                "profiles.photo.upload", [LockLevel.ACCOUNT, LockLevel.PROFILE, LockLevel.INSERT]
            ),
        ):
            profile = _lock_own_profile(user, profile_id)
            if live_photos(profile.id).count() >= settings.PHOTO_MAX_PER_PROFILE:
                raise PhotoLimitReached()
            photo = ProfilePhoto.objects.create(
                profile=profile, uploaded_by=user, photo_type=photo_type
            )
            stored_key = default_storage.save(_quarantine_key(photo), ContentFile(data))
            _audit(user, profile, "profile.photo_uploaded")
            from ..tasks import process_photo

            transaction.on_commit(lambda: process_photo.delay(str(photo.id)))
    except Exception:
        if stored_key:
            default_storage.delete(stored_key)  # the row rolled back; drop the orphan
        raise
    return photo


# --- Processing (Celery task body) ---------------------------------------------------------


def _reencode(data: bytes) -> tuple[bytes, int, int]:
    """Decode, verify, orient, bound and re-encode. Raises ValueError for unusable input."""
    Image.MAX_IMAGE_PIXELS = settings.PHOTO_MAX_PIXELS
    try:
        with Image.open(io.BytesIO(data)) as probe:  # header only: no pixels decoded yet
            if probe.width * probe.height > settings.PHOTO_MAX_PIXELS:
                raise ValueError("TOO_LARGE")
            probe.verify()
        with Image.open(io.BytesIO(data)) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode not in ("RGB", "L"):
                rgba = image.convert("RGBA")
                image = Image.new("RGB", rgba.size, (255, 255, 255))
                image.paste(rgba, mask=rgba.getchannel("A"))
            else:
                image = image.convert("RGB")
            if min(image.size) < settings.PHOTO_MIN_EDGE:
                raise ValueError("TOO_SMALL")
            image.thumbnail((settings.PHOTO_MAX_EDGE, settings.PHOTO_MAX_EDGE))
            out = io.BytesIO()
            # A fresh save with no exif/icc/xmp arguments writes no metadata.
            image.save(out, format="JPEG", quality=85, optimize=True, progressive=True)
            return out.getvalue(), image.width, image.height
    except ValueError:
        raise
    except Image.DecompressionBombError:
        raise ValueError("TOO_LARGE") from None
    except Exception:
        raise ValueError("INVALID_IMAGE") from None


def _reject(photo_id, reason: str) -> None:
    ProfilePhoto.objects.filter(pk=photo_id, processing_status="QUARANTINED").update(
        processing_status="REJECTED", rejection_reason=reason, updated_at=timezone.now()
    )


def process_photo(photo_id) -> str:
    photo = ProfilePhoto.objects.filter(pk=photo_id).first()
    if photo is None or photo.processing_status != ProfilePhoto.Processing.QUARANTINED:
        return "skipped"  # idempotent: already processed or rejected
    quarantine = _quarantine_key(photo)
    try:
        if photo.deleted_at is not None:
            _reject(photo.id, "DELETED_BEFORE_PROCESSING")
            return "rejected"
        if not default_storage.exists(quarantine):
            _reject(photo.id, "MISSING_UPLOAD")
            return "rejected"
        with default_storage.open(quarantine, "rb") as handle:
            data = handle.read()
        kind = filetype.guess(data)
        if kind is None or kind.mime not in ACCEPTED_MIME:
            _reject(photo.id, "UNSUPPORTED_TYPE")
            return "rejected"
        try:
            scan = get_malware_scanner().scan(data)
        except ProviderDisabledError:
            _reject(photo.id, "SCAN_UNAVAILABLE")
            return "rejected"
        if not scan.clean:
            _reject(photo.id, "MALWARE_DETECTED")
            logger.warning("Upload rejected by the malware scanner", extra={"photo": str(photo.id)})
            return "rejected"
        try:
            output, width, height = _reencode(data)
        except ValueError as exc:
            _reject(photo.id, str(exc))
            return "rejected"

        final_key = default_storage.save(_final_key(photo), ContentFile(output))
        with (
            transaction.atomic(),
            lock_plan("profiles.photo.process", [LockLevel.PROFILE, LockLevel.DOMAIN]),
        ):
            lock_rows_for_update(
                MatrimonialProfile.objects.filter(pk=photo.profile_id), LockLevel.PROFILE
            )
            rows = lock_rows_for_update(
                ProfilePhoto.objects.filter(
                    pk=photo.id, processing_status="QUARANTINED", deleted_at__isnull=True
                ),
                LockLevel.DOMAIN,
            )
            if not rows:  # deleted or processed meanwhile
                transaction.on_commit(lambda: default_storage.delete(final_key))
                _reject(photo.id, "DELETED_BEFORE_PROCESSING")
                return "rejected"
            row = rows[0]
            row.processing_status = ProfilePhoto.Processing.READY
            row.storage_key = final_key
            row.mime_type = OUTPUT_MIME
            row.size = len(output)
            row.checksum = hashlib.sha256(output).hexdigest()
            row.width, row.height = width, height
            # The first ready photo becomes primary if none is.
            row.is_primary = not live_photos(row.profile_id).filter(is_primary=True).exists()
            row.save()
        return "ready"
    finally:
        default_storage.delete(quarantine)  # the original is always discarded


# --- Owner management ----------------------------------------------------------------------


def update_photo(user: User, profile_id, photo_id, data: dict) -> ProfilePhoto:
    with (
        transaction.atomic(),
        lock_plan(
            "profiles.photo.update", [LockLevel.ACCOUNT, LockLevel.PROFILE, LockLevel.DOMAIN]
        ),
    ):
        profile = _lock_own_profile(user, profile_id)
        rows = lock_rows_for_update(live_photos(profile.id), LockLevel.DOMAIN)
        photo = next((p for p in rows if p.pk == photo_id), None)
        if photo is None:
            raise NotFound()
        if "photo_type" in data:
            if data["photo_type"] is not None and not reference.is_allowed(
                "photo_type", data["photo_type"], current=photo.photo_type
            ):
                raise ValidationError({"photo_type": ["Unknown photo type."]})
            photo.photo_type = data["photo_type"]
        if data.get("is_primary") is True:
            if (
                photo.processing_status != ProfilePhoto.Processing.READY
                or photo.moderation_status == ProfilePhoto.Moderation.REJECTED
            ):
                raise ValidationError({"is_primary": ["Only a processed photo can be primary."]})
            for other in rows:
                if other.is_primary and other.pk != photo.pk:
                    other.is_primary = False
                    other.save(update_fields=["is_primary", "updated_at"])
            photo.is_primary = True
        elif data.get("is_primary") is False:
            photo.is_primary = False
        photo.save(update_fields=["photo_type", "is_primary", "updated_at"])
    return photo


def delete_photo(user: User, profile_id, photo_id) -> None:
    with (
        transaction.atomic(),
        lock_plan(
            "profiles.photo.delete", [LockLevel.ACCOUNT, LockLevel.PROFILE, LockLevel.DOMAIN]
        ),
    ):
        profile = _lock_own_profile(user, profile_id)
        rows = lock_rows_for_update(live_photos(profile.id).filter(pk=photo_id), LockLevel.DOMAIN)
        if not rows:
            raise NotFound()
        photo = rows[0]
        photo.deleted_at = timezone.now()
        photo.is_primary = False
        photo.save(update_fields=["deleted_at", "is_primary", "updated_at"])
        _audit(user, profile, "profile.photo_deleted")
        if photo.storage_key:
            key = photo.storage_key
            transaction.on_commit(lambda: default_storage.delete(key))
