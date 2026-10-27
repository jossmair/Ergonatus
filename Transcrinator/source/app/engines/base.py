from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Transcript:
    identity: str
    text: str
    final: bool
    received_at: float


class Engine(ABC):
    backend: str = "inconnu"
    ready: bool = False

    @abstractmethod
    async def load(self): ...

    @abstractmethod
    async def begin(self, emit: Callable[[Transcript], None]): ...

    @abstractmethod
    async def feed(self, audio): ...

    @abstractmethod
    async def finish(self): ...

    @abstractmethod
    async def close(self): ...
