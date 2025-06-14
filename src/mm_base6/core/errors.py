class UserError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class UnregisteredSettingError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class UnregisteredStateError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
