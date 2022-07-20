class HeliosException(Exception):
    ...


class IdMismatchError(HeliosException):
    ...


class NotFoundError(HeliosException):
    ...


class DecodingError(HeliosException):
    ...


class HTTPError(HeliosException):
    def __init__(self, status_code: int, message: str, *args):
        super().__init__(f'Error Code: {status_code}: {message}', *args)
