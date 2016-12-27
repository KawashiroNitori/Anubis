

class Error(Exception):
    pass


class HashError(Error):
    pass


class InvalidStateError(Error):
    pass


class UserFacingError(Error):

    def to_dict(self):
        return {'name': self.__class__.__name__, 'args': self.args}

    @property
    def http_status(self):
        return 500

    @property
    def template_name(self):
        return 'error.html'

    @property
    def message(self):
        return 'An error has occurred.'


class ForbiddenError(UserFacingError):
    @property
    def http_status(self):
        return 403


class NotFoundError(UserFacingError):
    @property
    def http_status(self):
        return 404

    @property
    def message(self):
        return 'path {0} not found.'


class ValidationError(ForbiddenError):
    @property
    def message(self):
        if len(self.args) == 1:
            return 'Field {0} validation failed.'
        elif len(self.args) == 2:
            return 'Field {0} or {1} validation failed.'


class UnknownFieldError(ForbiddenError):
    @property
    def message(self):
        return 'Unknown field {0}.'


class InvalidTokenError(ForbiddenError):
    pass


class VerifyPasswordError(ForbiddenError):
    # Error with the `VERIFY PASSWORD` , not password verification error.
    @property
    def message(self):
        return 'Passwords don\'t match.'


class UserAlreadyExistError(ForbiddenError):
    @property
    def message(self):
        return 'User {0} already exists.'
