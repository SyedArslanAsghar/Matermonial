"""Manager permission catalogue and starter templates: the approved doc 14 §3–§5 baseline.

Doc 14 §9 (tiers N/S/H/O, new codes, pre-selection) is OD-05 (OPEN) and isn't implemented.
The catalogue is seeded by migration ``family.0002`` from a frozen copy of these tuples and is
then data: administrators can deactivate entries or edit templates in the Django Admin.

``manage_family_authorizations`` and ``manage_verification_submission`` are **Owner-only**
(owner decision DR-2026-11-20-O-4, OD-05c; migration ``family.0004``): a manager never manages
other managers and never submits identity verification for the owner. The first is also seeded
inactive. Owner-only permissions are never granted, and a stored grant is ignored at use.
"""

NORMAL, SENSITIVE, OWNER_ONLY = "NORMAL", "SENSITIVE", "OWNER_ONLY"

# (code, description, sensitivity) — doc 14 §3
PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    ("view_profile", "View represented profile", NORMAL),
    ("edit_basic_info", "Edit permitted basic information", NORMAL),
    ("edit_education", "Edit education", NORMAL),
    ("edit_profession", "Edit profession", NORMAL),
    ("edit_family_details", "Edit family details", NORMAL),
    ("manage_photos", "Upload, update, or remove photos", NORMAL),
    ("view_partner_preferences", "View partner preferences", NORMAL),
    ("edit_partner_preferences", "Edit partner preferences", NORMAL),
    ("search_profiles", "Search on behalf of profile", NORMAL),
    ("view_interests", "View sent and received interests", NORMAL),
    ("send_interests", "Express interest", NORMAL),
    ("respond_to_interests", "Respond to received interests", NORMAL),
    ("send_requests", "Send formal requests", NORMAL),
    ("respond_to_requests", "Accept or decline requests", NORMAL),
    ("withdraw_requests", "Withdraw pending requests", NORMAL),
    ("view_connections", "View connections", NORMAL),
    ("manage_relationship_progress", "Update relationship progress", NORMAL),
    ("view_conversations", "View authorized conversations", SENSITIVE),
    ("send_messages", "Send messages on behalf of profile", SENSITIVE),
    ("upload_attachments", "Upload conversation attachments", SENSITIVE),
    ("view_shared_documents", "View documents shared with profile", SENSITIVE),
    ("share_documents", "Share owner's private documents", SENSITIVE),
    ("manage_document_permissions", "Grant or revoke document access", SENSITIVE),
    ("view_privacy_settings", "View privacy settings", SENSITIVE),
    ("manage_privacy_settings", "Change privacy settings", SENSITIVE),
    ("view_blocked_profiles", "View block list", SENSITIVE),
    ("manage_blocked_profiles", "Block/unblock profiles", SENSITIVE),
    ("view_hidden_profiles", "View Hide My Profile From list", SENSITIVE),
    ("manage_hidden_profiles", "Hide/unhide profiles", SENSITIVE),
    ("view_visitor_history", "View profile visitors", SENSITIVE),
    ("manage_visitor_history", "Remove/clear visible visitor records", SENSITIVE),
    ("manage_family_authorizations", "Invite and manage other managers", OWNER_ONLY),
    ("view_verification_status", "View verification status", SENSITIVE),
    ("manage_verification_submission", "Submit/resubmit verification", OWNER_ONLY),
    ("view_financial_summary", "View subscription and credit summary", SENSITIVE),
    ("manage_subscription", "Purchase or cancel subscription", SENSITIVE),
    ("manage_account_security", "Change account security settings", OWNER_ONLY),
    ("request_data_export", "Request account data export", OWNER_ONLY),
    ("request_account_deletion", "Request account deletion", OWNER_ONLY),
)
INACTIVE_AT_SEED = {"manage_family_authorizations"}

_STANDARD = (
    "view_profile",
    "edit_basic_info",
    "edit_family_details",
    "edit_education",
    "edit_profession",
    "view_partner_preferences",
    "search_profiles",
    "view_interests",
    "send_interests",
    "view_connections",
)
_COMMUNICATION = (
    "view_profile",
    "search_profiles",
    "view_interests",
    "send_interests",
    "send_requests",
    "respond_to_requests",
    "view_connections",
    "view_conversations",
    "send_messages",
    "manage_relationship_progress",
)
_ADVANCED_EXTRA = ("manage_photos", "upload_attachments", "view_shared_documents")

# (code, name, permissions) — doc 14 §4. Sensitive entries are listed but never granted by
# applying a template (doc 14 §4): they need explicit owner confirmation.
TEMPLATES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("standard", "Standard Manager", _STANDARD),
    ("communication", "Communication Manager", _COMMUNICATION),
    (
        "advanced",
        "Advanced Manager",
        tuple(dict.fromkeys(_STANDARD + _COMMUNICATION + _ADVANCED_EXTRA)),
    ),
)
