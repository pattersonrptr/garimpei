"""What admin asks the other modules. Admin owns these ports; the adapters in
``admin/adapters/`` implement them over the other modules' use cases."""

from abc import ABC, abstractmethod

from src.app.admin.entities import Counts, RecentRun


class PlatformStats(ABC):
    """The numbers of the platform the admin summary shows."""

    @abstractmethod
    def users(self) -> Counts:
        """All users and the active ones."""
        raise NotImplementedError

    @abstractmethod
    def alerts(self) -> Counts:
        """All price alerts and the active ones, soft-deleted ones left out."""
        raise NotImplementedError

    @abstractmethod
    def products(self) -> int:
        """How many products there are, available or not."""
        raise NotImplementedError

    @abstractmethod
    def stores(self) -> Counts:
        """All stores and the active ones."""
        raise NotImplementedError

    @abstractmethod
    def recent_runs(self, limit: int) -> list[RecentRun]:
        """The latest ``limit`` runs of saved searches, newest first."""
        raise NotImplementedError
