from collections.abc import MutableSequence, Sequence, Iterable
from fractions import Fraction
import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from _typeshed import SupportsLenAndGetItem

_T = typing.TypeVar('_T')


# Pycharm doesn't like this, but mypy and the docs say it's correct.
class RNGType(typing.Protocol):
    """
    Protocol so that I can pass the module random or an instance of random.Random
    """
    def random(self) -> float: ...
    def seed(self, a: int | float | str | bytes | bytearray | None = None, version=2): ...
    def shuffle(self, x: MutableSequence[_T]): ...
    def choice(self, seq: "SupportsLenAndGetItem[_T]") -> _T: ...

    def choices(
            self,
            population: "SupportsLenAndGetItem[_T]",
            weights: Sequence[float | Fraction] | None = None,
            *,
            cum_weights: Sequence[float | Fraction] | None = None,
            k: int = 1
    ) -> list: ...

    def randint(self,
                a: int,
                b: int) -> int: ...

    def randrange(self,
                  start: int,
                  stop: int | None = None,
                  step: int = 1) -> int: ...

    def sample(self,
               population: Sequence[_T],
               k: int,
               *,
               counts: Iterable[int] | None = None) -> list[_T]: ...

    def uniform(self,
            a: float,
            b: float) -> float: ...