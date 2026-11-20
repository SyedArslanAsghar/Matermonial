from django.urls import path

from . import views

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notifications"),
    path("read-all/", views.NotificationReadAllView.as_view(), name="notifications-read-all"),
    path(
        "<uuid:notification_id>/read/",
        views.NotificationReadView.as_view(),
        name="notification-read",
    ),
    path("devices/", views.DeviceRegisterView.as_view(), name="push-devices"),
    path(
        "devices/unregister/",
        views.DeviceUnregisterView.as_view(),
        name="push-devices-unregister",
    ),
]
