"""Exceptions for the OpenRouter provider boundary.

All provider failures surface as these typed exceptions so callers (the extraction
harness in TKT-0034) can distinguish a provider fault from a contract violation without
inspecting HTTP internals.
"""

from __future__ import annotations


class OpenRouterError(Exception):
    """Base exception for all OpenRouter provider failures."""


class OpenRouterAuthError(OpenRouterError):
    """The configured API key is missing, invalid, or unauthorized."""


class OpenRouterTimeoutError(OpenRouterError):
    """A request exceeded the configured timeout after all retries."""


class OpenRouterRateLimitError(OpenRouterError):
    """The provider returned a rate-limit response after all retries."""


class OpenRouterContractError(OpenRouterError):
    """A provider response could not be validated against the typed contract."""


class OpenRouterServerError(OpenRouterError):
    """The provider returned a server error (5xx) after all retries."""
