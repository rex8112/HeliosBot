class HeliosException(Exception):
    pass


class IdMismatchError(HeliosException):
    pass


class NotFoundError(HeliosException):
    pass
