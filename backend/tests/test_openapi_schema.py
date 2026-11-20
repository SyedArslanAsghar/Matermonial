"""KI-40: the OpenAPI schema generates with zero errors and zero warnings, validates against the
OpenAPI specification, and declares what the views actually return."""

import io

import pytest
import yaml
from django.core.management import call_command


@pytest.fixture(scope="module")
def schema(tmp_path_factory):
    path = tmp_path_factory.mktemp("schema") / "schema.yaml"
    stderr = io.StringIO()
    # --validate checks the document against the OpenAPI 3 JSON schema; --fail-on-warn turns
    # every generator warning or error into a failure.
    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(path), stderr=stderr)
    assert "Error" not in stderr.getvalue() and "Warning" not in stderr.getvalue()
    return yaml.safe_load(path.read_text())


def operation(schema, path, method):
    return schema["paths"][f"/api/v1/{path}"][method]


def test_every_api_operation_has_a_response_schema(schema):
    for path, item in schema["paths"].items():
        for method, op in item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            assert op["responses"], (path, method)
            for code, response in op["responses"].items():
                if code != "204":
                    assert "content" in response, (path, method, code)


def test_security_schemes_describe_the_real_authentication(schema):
    schemes = schema["components"]["securitySchemes"]
    assert schemes["bearerToken"] == {
        "type": "http",
        "scheme": "bearer",
        "description": schemes["bearerToken"]["description"],
    }
    assert schemes["webSession"]["in"] == "cookie"


def test_invitations_and_requests_document_202_and_permission_selection(schema):
    invite = operation(schema, "family-management/authorizations/", "post")
    assert "202" in invite["responses"]
    request_body = invite["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    fields = schema["components"]["schemas"][request_body.rsplit("/", 1)[-1]]["properties"]
    assert {"phone_number", "permission_group", "permissions", "confirm_sensitive"} <= set(fields)
    assert "202" in operation(schema, "family-management/requests/", "post")["responses"]
    accept = operation(schema, "family-management/requests/{request_id}/accept/", "post")
    assert accept["requestBody"]


def test_step_up_and_acting_profile_headers_are_documented(schema):
    step_up = operation(schema, "profiles/step-up/", "post")
    assert any(p["name"] == "X-Acting-Profile" and p["required"] for p in step_up["parameters"])
    patch_me = operation(schema, "profiles/me/", "patch")
    assert {"X-Acting-Profile", "X-Step-Up-Verification"} <= {
        p["name"] for p in patch_me["parameters"]
    }


def test_photo_upload_is_multipart_and_never_returns_storage_details(schema):
    upload = operation(schema, "profiles/{profile_id}/photos/", "post")
    assert "multipart/form-data" in upload["requestBody"]["content"]
    photo = schema["components"]["schemas"]["Photo"]["properties"]
    assert "storage_key" not in photo and "url" not in photo


@pytest.mark.django_db
def test_family_response_builders_match_their_declared_schemas():
    """Drift guard: the dicts the views build have exactly the documented fields."""
    from apps.family.api import serializers as s
    from apps.family.api import views

    builders = {
        views._as_owner: s.OwnerAuthorizationSerializer,
        views._as_manager: s.ManagedAuthorizationSerializer,
        views._as_invitation: s.InvitationSerializer,
        views._as_sent_request: s.SentRequestSerializer,
        views._as_received_request: s.ReceivedRequestSerializer,
    }
    import inspect

    for builder, serializer in builders.items():
        source = inspect.getsource(builder)
        declared = set(serializer().fields)
        returned = {
            line.split('"')[1]
            for line in source.splitlines()
            if line.strip().startswith('"') and '":' in line
        }
        assert returned == declared, (builder.__name__, returned ^ declared)


def test_photo_response_schema_matches_the_view_fields():
    from apps.profiles.api.photos import FIELDS, PhotoSerializer

    assert set(PhotoSerializer().fields) == set(FIELDS)


@pytest.mark.django_db
def test_profile_response_has_exactly_the_declared_fields():
    from apps.accounts.models import User
    from apps.profiles.api.serializers import OwnProfileSerializer
    from apps.profiles.services.profiles import create_profile

    user = User.objects.create_user(phone_number="+923001112233", password="Pw-Long-enough-9")
    User.objects.filter(pk=user.pk).update(is_phone_verified=True)
    profile = create_profile(User.objects.get(pk=user.pk))
    body = OwnProfileSerializer(profile).data
    assert set(body) == set(OwnProfileSerializer().fields)
