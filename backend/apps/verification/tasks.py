"""OTP dispatch (CC-R53: asynchronous OTP dispatch). Arguments are never logged (BaseTask)."""

import logging

from celery import shared_task

from common.providers import get_sms_provider

from .models import PhoneVerification

logger = logging.getLogger(__name__)


@shared_task(name="verification.send_otp_sms")
def send_otp_sms(verification_id: str, code: str) -> None:
    verification = PhoneVerification.objects.filter(id=verification_id, status="PENDING").first()
    if verification is None:  # superseded or already used: never send a dead code
        return
    minutes = max(1, (verification.expires_at - verification.created_at).seconds // 60)
    result = get_sms_provider().send_sms(
        to=verification.phone_number,
        message=f"Your Matermonial code is {code}. It expires in {minutes} minutes. "
        "Never share it.",
    )
    # Acceptance by the provider isn't proof of delivery (CC-R54).
    PhoneVerification.objects.filter(id=verification_id).update(provider_reference=result.reference)
    logger.info("OTP dispatched", extra={"provider": result.provider})
