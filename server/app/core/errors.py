class AppError(Exception):
    """Base of the errors the API turns into HTTP responses."""

    status_code = 500

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__


class DeviceNotFoundError(AppError):
    status_code = 404


class DeviceUnreachableError(AppError):
    """The device exists but did not acknowledge the command (asleep, out of range...)."""

    status_code = 502


class UnsupportedCommandError(AppError):
    status_code = 422


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class RadioNotReadyError(AppError):
    status_code = 503
