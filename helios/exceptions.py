class HeliosException(Exception):
    ...


class IdMismatchError(HeliosException):
    ...


class NotFoundError(HeliosException):
    ...


class DecodingError(HeliosException):
    ...
