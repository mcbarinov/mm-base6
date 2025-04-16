class UserError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class UnregisteredDynamicConfigError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class UnregisteredDynamicValueError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
