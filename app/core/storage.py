import os
from typing import IO


class LocalStorage:
    def __init__(self, base_path: str = './uploads'):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def save(self, file_obj: IO, filename: str) -> str:
        path = os.path.join(self.base_path, filename)
        with open(path, 'wb') as f:
            f.write(file_obj.read())
        return path


storage = LocalStorage()
