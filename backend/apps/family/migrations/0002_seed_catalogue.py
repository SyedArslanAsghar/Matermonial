"""Seed the doc 14 §3 permission catalogue and the §4 starter templates (frozen copy).

``manage_family_authorizations`` is seeded inactive (owner-only by decided rule; OD-05c). The
reverse removes only rows this migration created and that nothing references.
"""

from django.db import migrations

PERMISSIONS = (('view_profile', 'View represented profile', 'NORMAL'), ('edit_basic_info', 'Edit permitted basic information', 'NORMAL'), ('edit_education', 'Edit education', 'NORMAL'), ('edit_profession', 'Edit profession', 'NORMAL'), ('edit_family_details', 'Edit family details', 'NORMAL'), ('manage_photos', 'Upload, update, or remove photos', 'NORMAL'), ('view_partner_preferences', 'View partner preferences', 'NORMAL'), ('edit_partner_preferences', 'Edit partner preferences', 'NORMAL'), ('search_profiles', 'Search on behalf of profile', 'NORMAL'), ('view_interests', 'View sent and received interests', 'NORMAL'), ('send_interests', 'Express interest', 'NORMAL'), ('respond_to_interests', 'Respond to received interests', 'NORMAL'), ('send_requests', 'Send formal requests', 'NORMAL'), ('respond_to_requests', 'Accept or decline requests', 'NORMAL'), ('withdraw_requests', 'Withdraw pending requests', 'NORMAL'), ('view_connections', 'View connections', 'NORMAL'), ('manage_relationship_progress', 'Update relationship progress', 'NORMAL'), ('view_conversations', 'View authorized conversations', 'SENSITIVE'), ('send_messages', 'Send messages on behalf of profile', 'SENSITIVE'), ('upload_attachments', 'Upload conversation attachments', 'SENSITIVE'), ('view_shared_documents', 'View documents shared with profile', 'SENSITIVE'), ('share_documents', "Share owner's private documents", 'SENSITIVE'), ('manage_document_permissions', 'Grant or revoke document access', 'SENSITIVE'), ('view_privacy_settings', 'View privacy settings', 'SENSITIVE'), ('manage_privacy_settings', 'Change privacy settings', 'SENSITIVE'), ('view_blocked_profiles', 'View block list', 'SENSITIVE'), ('manage_blocked_profiles', 'Block/unblock profiles', 'SENSITIVE'), ('view_hidden_profiles', 'View Hide My Profile From list', 'SENSITIVE'), ('manage_hidden_profiles', 'Hide/unhide profiles', 'SENSITIVE'), ('view_visitor_history', 'View profile visitors', 'SENSITIVE'), ('manage_visitor_history', 'Remove/clear visible visitor records', 'SENSITIVE'), ('manage_family_authorizations', 'Invite and manage other managers', 'SENSITIVE'), ('view_verification_status', 'View verification status', 'SENSITIVE'), ('manage_verification_submission', 'Submit/resubmit verification', 'SENSITIVE'), ('view_financial_summary', 'View subscription and credit summary', 'SENSITIVE'), ('manage_subscription', 'Purchase or cancel subscription', 'SENSITIVE'), ('manage_account_security', 'Change account security settings', 'OWNER_ONLY'), ('request_data_export', 'Request account data export', 'OWNER_ONLY'), ('request_account_deletion', 'Request account deletion', 'OWNER_ONLY'))
INACTIVE = ['manage_family_authorizations']
TEMPLATES = (('standard', 'Standard Manager', ('view_profile', 'edit_basic_info', 'edit_family_details', 'edit_education', 'edit_profession', 'view_partner_preferences', 'search_profiles', 'view_interests', 'send_interests', 'view_connections')), ('communication', 'Communication Manager', ('view_profile', 'search_profiles', 'view_interests', 'send_interests', 'send_requests', 'respond_to_requests', 'view_connections', 'view_conversations', 'send_messages', 'manage_relationship_progress')), ('advanced', 'Advanced Manager', ('view_profile', 'edit_basic_info', 'edit_family_details', 'edit_education', 'edit_profession', 'view_partner_preferences', 'search_profiles', 'view_interests', 'send_interests', 'view_connections', 'send_requests', 'respond_to_requests', 'view_conversations', 'send_messages', 'manage_relationship_progress', 'manage_photos', 'upload_attachments', 'view_shared_documents')))


def seed(apps, schema_editor):
    Permission = apps.get_model("family", "ManagerPermission")
    Group = apps.get_model("family", "ManagerPermissionGroup")
    Link = apps.get_model("family", "ManagerPermissionGroupPermission")
    for code, name, sensitivity in PERMISSIONS:
        Permission.objects.get_or_create(
            code=code,
            defaults={"name": name, "sensitivity": sensitivity, "is_active": code not in INACTIVE},
        )
    for code, name, codes in TEMPLATES:
        group, _ = Group.objects.get_or_create(
            code=code, defaults={"name": name, "is_system_default": True}
        )
        for permission in Permission.objects.filter(code__in=codes):
            Link.objects.get_or_create(group=group, permission=permission)


def unseed(apps, schema_editor):
    apps.get_model("family", "ManagerPermissionGroupPermission").objects.all().delete()
    apps.get_model("family", "ManagerPermissionGroup").objects.filter(is_system_default=True).delete()
    apps.get_model("family", "ManagerPermission").objects.filter(
        code__in=[p[0] for p in PERMISSIONS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("family", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
