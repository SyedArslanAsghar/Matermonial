from django.urls import path

from . import views
from .preferences import PartnerPreferenceView

urlpatterns = [
    path("", views.ProfileCreateView.as_view(), name="profile-create"),
    path("me/", views.OwnProfileView.as_view(), name="profile-me"),
    path("me/partner-preferences/", PartnerPreferenceView.as_view(), name="partner-preferences"),
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
]
