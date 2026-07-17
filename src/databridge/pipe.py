from typing import Generic, TypeVar
from collections.abc import Callable

T = TypeVar("T")
U = TypeVar("U")


class Pipe(Generic[T]):
    def __init__(self, value: T):
        self.value = value

    def then(self, fn: Callable[[T], U]) -> "Pipe[U]":
        return Pipe(fn(self.value))

    def unwrap(self) -> T:
        return self.value
