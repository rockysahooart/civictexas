"""Provider-agnostic model interface.

To add a real model, implement `SummaryProvider.generate` with that vendor's
SDK, return the raw JSON text, and register it in `get_provider`. Keep API keys
in server-side environment variables (SUMMARY_API_KEY). Nothing else in the
pipeline needs to change.
"""
import json
import os
from typing import Dict, Optional, Protocol

from .prompt import Prompt


class SummaryProvider(Protocol):
    name: str
    model_id: str

    def generate(self, prompt: Prompt) -> str:
        """Return the model's raw JSON response."""


class NotConfiguredError(RuntimeError):
    pass


class StaticProvider:
    """Returns prepared outputs. Used by tests and the evaluation harness only."""

    name = "static"

    def __init__(self, outputs: Dict[str, object], model_id: str = "static-fixture"):
        self.outputs = outputs
        self.model_id = model_id
        self.calls = 0

    def generate(self, prompt: Prompt) -> str:
        self.calls += 1
        for key, output in self.outputs.items():
            if key in prompt.user:
                return output if isinstance(output, str) else json.dumps(output)
        raise KeyError("no prepared output matches this prompt")


def get_provider(name: Optional[str] = None) -> SummaryProvider:
    name = name or os.environ.get("SUMMARY_PROVIDER", "")
    if not name:
        raise NotConfiguredError(
            "No summary provider is configured. Set SUMMARY_PROVIDER, SUMMARY_MODEL and SUMMARY_API_KEY "
            "after adding a provider adapter in summarization/civictexas_summarize/providers.py.")
    raise NotConfiguredError(f"Unknown summary provider {name!r}")
