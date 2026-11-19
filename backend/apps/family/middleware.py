"""Account-scoped API endpoints refuse ``X-Acting-Profile`` (doc 04 §24.1 step 2).

Only ``/api/v1/profiles/…`` endpoints are profile-scoped today (each resolves an ActorContext);
``POST /api/v1/profiles/`` (create) refuses the header in its view. Later phases add their
profile-scoped prefixes here.
"""

from django.http import JsonResponse

from common.api.exceptions import error_body

PROFILE_SCOPED_PREFIXES = ("/api/v1/profiles/",)


class ActingProfileHeaderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if (
            request.META.get("HTTP_X_ACTING_PROFILE")
            and path.startswith("/api/")
            and not path.startswith(PROFILE_SCOPED_PREFIXES)
        ):
            return JsonResponse(
                error_body(
                    "header_not_allowed", "X-Acting-Profile isn't accepted by this endpoint."
                ),
                status=400,
            )
        return self.get_response(request)
