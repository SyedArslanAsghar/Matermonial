from django.urls import path

from . import views

urlpatterns = [
    path("authorizations/", views.AuthorizationListView.as_view(), name="family-authorizations"),
    path(
        "authorizations/<uuid:authorization_id>/accept/",
        views.ManagerResponseView.as_view(accept=True),
        name="family-accept",
    ),
    path(
        "authorizations/<uuid:authorization_id>/reject/",
        views.ManagerResponseView.as_view(accept=False),
        name="family-reject",
    ),
    path(
        "authorizations/<uuid:authorization_id>/pause/",
        views.PauseView.as_view(),
        name="family-pause",
    ),
    path(
        "authorizations/<uuid:authorization_id>/resume/",
        views.ResumeView.as_view(),
        name="family-resume",
    ),
    path(
        "authorizations/<uuid:authorization_id>/revoke/",
        views.RevokeView.as_view(),
        name="family-revoke",
    ),
    path(
        "authorizations/<uuid:authorization_id>/renew/",
        views.RenewView.as_view(),
        name="family-renew",
    ),
    path(
        "authorizations/<uuid:authorization_id>/permissions/",
        views.AuthorizationPermissionsView.as_view(),
        name="family-permissions",
    ),
    path(
        "authorizations/<uuid:authorization_id>/history/",
        views.AuthorizationHistoryView.as_view(),
        name="family-history",
    ),
    path(
        "invitations/<uuid:invitation_id>/cancel/",
        views.InvitationCancelView.as_view(),
        name="family-invitation-cancel",
    ),
    path("permissions/", views.PermissionCatalogueView.as_view(), name="family-catalogue"),
    path("permission-groups/", views.PermissionGroupView.as_view(), name="family-groups"),
    path(
        "profile-access-history/",
        views.ProfileAccessHistoryView.as_view(),
        name="family-access-history",
    ),
]
