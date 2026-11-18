"""Authentication error codes (doc 04 §24.4; doc 06 §22.1). Messages never reveal whether an
account, phone or session exists."""

from rest_framework import status
from rest_framework.exceptions import APIException


class InvalidCredentials(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "invalid_credentials"
    default_detail = "Invalid phone number or password."


class SessionRevoked(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "session_revoked"
    default_detail = "Your session has ended. Please sign in again."


class SessionExpired(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "session_expired"
    default_detail = "Your session has expired. Please sign in again."


class InvalidToken(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "invalid_token"
    default_detail = "The token is not valid."


class AmbiguousCredentials(APIException):
    """doc 06 §22.1: a request carrying both a session cookie and a bearer token is rejected."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "ambiguous_credentials"
    default_detail = "Send either a session cookie or a bearer token, not both."


class AccountUnavailable(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "account_unavailable"
    default_detail = "This account can't be used right now."


class InvalidCode(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "invalid_code"
    default_detail = "The code is invalid or has expired."


class StepUpRequired(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "step_up_required"
    default_detail = "Please confirm your password to continue."
