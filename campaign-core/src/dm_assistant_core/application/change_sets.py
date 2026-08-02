"""Application service for the sole canonical mutation operation."""

from typing import Protocol

from dm_assistant_core.domain.change_sets import ApplyChangeSetCommand, ChangeSetReceipt


class ChangeSetRepository(Protocol):
    """Persistence port whose implementation invokes the atomic database function."""

    def apply(self, command: ApplyChangeSetCommand) -> ChangeSetReceipt: ...


class ChangeSetApplicationService:
    """Coordinate canonical application without leaking persistence into the domain."""

    def __init__(self, repository: ChangeSetRepository) -> None:
        self._repository = repository

    def apply(self, command: ApplyChangeSetCommand) -> ChangeSetReceipt:
        return self._repository.apply(command)
