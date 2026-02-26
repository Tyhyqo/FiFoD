class ExternalAPIError(Exception):
    pass


class DeviceNotFoundError(Exception):
    pass


class FilesNotFoundError(Exception):

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"Файлы не найдены в директории: {missing}")
