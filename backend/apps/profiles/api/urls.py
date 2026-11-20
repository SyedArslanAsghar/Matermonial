from django.urls import path

from apps.family.api.step_up import StepUpView

from . import views
from .photos import PhotoDetailView, PhotoListView
from .preferences import PartnerPreferenceView

urlpatterns = [
    path("", views.ProfileCreateView.as_view(), name="profile-create"),
    path("me/", views.OwnProfileView.as_view(), name="profile-me"),
    path("me/partner-preferences/", PartnerPreferenceView.as_view(), name="partner-preferences"),
    # TR-16 manager step-up (profile-scoped: X-Acting-Profile selects the managed profile).
    path("step-up/", StepUpView.as_view(), name="profile-step-up"),
    path(
        "<uuid:profile_id>/completion/",
        views.ProfileCompletionView.as_view(),
        name="profile-completion",
    ),
    path(
        "<uuid:profile_id>/submit-review/",
        views.SubmitForReviewView.as_view(),
        name="profile-submit-review",
    ),
    path("<uuid:profile_id>/photos/", PhotoListView.as_view(), name="profile-photos"),
    path(
        "<uuid:profile_id>/photos/<uuid:photo_id>/",
        PhotoDetailView.as_view(),
        name="profile-photo",
    ),
]
