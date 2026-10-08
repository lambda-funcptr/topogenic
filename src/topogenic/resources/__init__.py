from hashlib import sha3_512
from os import getenv
from pathlib import Path
from struct import pack

class Resource():
    def metadata() -> dict[str, object]:
        raise NotImplemented

    def hash() -> str:
        raise NotImplemented

    def contents() -> str:
        raise NotImplemented


FILE_STAT_HASH = getenv("TOPOGENIC_FILE_STAT_HASH", True)


class File():
    def __init__(self, path: str):
        self._path = Path(path)

        if not self._path.exists():
            raise FileNotFoundError

        if not self._path.is_file():
            raise RuntimeError

    def hash(self) -> str:
        sha3sum = sha3_512()
        stat = self._path.stat()

        if FILE_STAT_HASH:
            sha3sum.update(pack("!d", stat.st_ctime))
            sha3sum.update(pack("!d", stat.st_mtime))
            sha3sum.update(pack("!L", stat.st_ino))
        else:
            sha3sum.update(self.contents())

        return str(sha3sum.digest())

    def metadata(self) -> dict[str, object]:
        return {
            "stat": self._path.stat()
        }

    def contents(self) -> str:
        with self._path.open() as file:
            return file.read()
