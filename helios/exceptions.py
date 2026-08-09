class HeliosException(Exception):
    pass

class ServerException(HeliosException):
    pass

class DuplicateServerException(ServerException):
    pass