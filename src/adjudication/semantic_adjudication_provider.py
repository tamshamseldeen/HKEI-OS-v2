"""Provider-neutral semantic adjudication interface."""

from abc import ABC, abstractmethod

from .semantic_adjudication_request import SemanticAdjudicationRequest
from .semantic_adjudication_response import SemanticAdjudicationResponse


class SemanticAdjudicationProvider(ABC):
    """Define the synchronous contract for a semantic adjudication adapter.

    Implementations receive an already-built request after the caller has passed
    the adjudication gate. They must return a ``SemanticAdjudicationResponse``
    whose Topic and Format selections belong to the request candidate tuples,
    preserve the request input fingerprint, identify the provider and model,
    populate request and response schema versions, use categorical confidence,
    and include concise rationale, evidence references, and usage metadata.

    Implementations must not request or return hidden chain-of-thought. Short
    rationale, evidence references, and structured classifications are allowed.
    The provider does not build requests, decide gate eligibility, resolve final
    classifications, calculate Reader Intent, or calculate Risk.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the immutable identity name exposed by the adapter."""
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the immutable model identity exposed by the adapter."""
        raise NotImplementedError

    @abstractmethod
    def adjudicate(
        self,
        request: SemanticAdjudicationRequest,
    ) -> SemanticAdjudicationResponse:
        """Return one structured response for an already-authorized request."""
        raise NotImplementedError
