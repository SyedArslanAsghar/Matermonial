"""Notification texts per outbox event type (DR-2026-11-20-O-7). Texts are generic: they never
contain names, phone numbers or other private data, and they don't reveal hidden or blocked
relationships (CC-R50). Adding an event type here registers its handler."""

GENERIC = ("Matermonial", "You have a new update. Open the app to see it.")

CATALOGUE: dict[str, tuple[str, str]] = {
    "family.invitation_received": (
        "Family manager invitation",
        "You've been invited to help manage a profile. Open the app to accept or decline.",
    ),
    "family.invitation_accepted": ("Invitation accepted", "Your manager invitation was accepted."),
    "family.invitation_rejected": ("Invitation declined", "Your manager invitation was declined."),
    "family.invitation_expired": (
        "Invitation expired",
        "A manager invitation expired because it wasn't accepted within 30 days.",
    ),
    "family.authorization_paused": (
        "Access paused",
        "Your access to a managed profile was paused.",
    ),
    "family.authorization_resumed": (
        "Access resumed",
        "Your access to a managed profile was resumed.",
    ),
    "family.authorization_revoked": (
        "Access ended",
        "Your access to a managed profile has ended.",
    ),
    "family.authorization_renewed": (
        "Access updated",
        "The end date of your access to a managed profile changed.",
    ),
    "family.authorization_expired": ("Access expired", "A manager authorization has expired."),
    "family.permissions_changed": (
        "Permissions changed",
        "Your permissions for a managed profile were updated.",
    ),
    "family.sensitive_permissions_changed": (
        "Sensitive permissions changed",
        "Sensitive permissions on your profile were changed.",
    ),
    "family.sensitive_action": (
        "Sensitive action on your profile",
        "A manager performed a sensitive action on your profile. Review it in your activity.",
    ),
    "family.manager_request_received": (
        "Request to manage your profile",
        "Someone asked to help manage your profile. Open the app to accept or decline.",
    ),
    "family.manager_request_accepted": (
        "Request accepted",
        "Your request to manage a profile was accepted.",
    ),
    "family.manager_request_declined": (
        "Request declined",
        "Your request to manage a profile was declined.",
    ),
    "family.manager_request_expired": (
        "Request expired",
        "A request to manage a profile expired because it wasn't accepted within 30 days.",
    ),
    "security.admin_mfa_recovery": (
        "Security notice",
        "An administrator authenticator recovery step took place on an account you can see.",
    ),
    "security.admin_mfa_enrollment": (
        "Security notice",
        "An administrator authenticator enrollment code was issued for your account.",
    ),
}

# Only opaque identifiers are copied from the event payload into ``data``.
SAFE_DATA_KEYS = {
    "authorization_id",
    "managerinvitation_id",
    "managerrequest_id",
    "invitation_id",
    "action",
    "stage",
}
