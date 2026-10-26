class APIException(Exception):
    """Base class for errors that map to a JSON HTTP response."""

    status_code = 400
    code = "api_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundException(APIException):
    """Requested resource does not exist (404)."""

    status_code = 404
    code = "not_found"


class DuplicateException(APIException):
    """Resource already exists (409)."""

    status_code = 409
    code = "duplicate"


class ForbiddenException(APIException):
    """Caller may not access this resource (403)."""

    status_code = 403
    code = "forbidden"
