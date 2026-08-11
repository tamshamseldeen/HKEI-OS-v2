"""Provider-neutral secret resolution abstraction."""

from abc import ABC, abstractmethod


class SemanticAdjudicationSecretResolver(ABC):
    """Resolve named secrets without prescribing a backing store."""

    @abstractmethod
    def resolve(self, secret_name: str) -> str:
        """Return the secret value associated with ``secret_name``."""
        raise NotImplementedError
