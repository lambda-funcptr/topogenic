from typing import Iterator, Tuple


class Counter():
    def __init__(self, initial: int = 0, step: int = 1):
        self.current = initial
        self._initial = initial
        self._delta = 1

    def state(self) -> Tuple[int, int, int]:
        return (self.current, self._initial, self._delta)

    def __iter__(self) -> Iterator[int]:
        return self

    def __next__(self) -> int:
        count = self.current
        self.current += self._delta
        return count

    def __int__(self) -> int:
        return self.current

    def __repr__(self) -> str:
        return str(self.current)
