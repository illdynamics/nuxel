#!/usr/bin/env python3
"""The single InferenceRuntime contract used by the PenGuru scheduler.

Concrete adapters (llama.cpp, ONNX Runtime GenAI, standard ORT) implement this
interface.  The UI never sees engine-specific flags: it sees these events and
the resolved engine/provider/variant reported by ``info()``.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional

ENGINE_LLAMA = "llama.cpp"
ENGINE_ORT_GENAI = "onnxruntime-genai"
ENGINE_ORT = "onnxruntime"


class RuntimeError_(RuntimeError):
    """Typed runtime failure carrying a machine-readable code."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code


@dataclass(frozen=True)
class DeviceProfile:
    total_ram_bytes: int = 0
    available_ram_bytes: int = 0
    cpu_count: int = 1
    thermal_ok: bool = True
    battery_ok: bool = True
    provider: str = "CPU"


@dataclass(frozen=True)
class RuntimeProfile:
    engine: str
    package_format: str
    provider: str = "CPU"
    threads: int = 4
    context_limit: int = 4096
    batch_limit: int = 512
    memory_budget_bytes: int = 0


@dataclass(frozen=True)
class GenerationOptions:
    max_tokens: int = 256
    temperature: float = 0.7
    top_p: float = 0.9
    seed: int = -1
    stop: List[str] = field(default_factory=list)
    request_id: str = ""
    system_prompt: str = ""


@dataclass(frozen=True)
class InferenceEvent:
    kind: str                      # loading|loaded|token|progress|cancelled|oom|error|unloaded|done
    data: Dict[str, Any] = field(default_factory=dict)


class InferenceRuntime(abc.ABC):
    engine: str = ""
    package_format: str = ""

    @abc.abstractmethod
    def probe(self, device: DeviceProfile, profile: RuntimeProfile) -> Dict[str, Any]:
        """Report availability and the compiled execution providers."""

    @abc.abstractmethod
    def load(self, manifest: Dict[str, Any], package_dir: str,
             profile: RuntimeProfile) -> Dict[str, Any]:
        """Load a verified package.  Raise RuntimeError_ on failure."""

    @abc.abstractmethod
    def generate(self, prompt: str, options: GenerationOptions
                 ) -> Iterator[InferenceEvent]:
        """Yield bounded events.  Cancellation is checked per token."""

    @abc.abstractmethod
    def cancel(self, request_id: str) -> Dict[str, Any]:
        ...

    @abc.abstractmethod
    def health(self) -> Dict[str, Any]:
        ...

    @abc.abstractmethod
    def unload(self, reason: str) -> Dict[str, Any]:
        ...

    @abc.abstractmethod
    def info(self) -> Dict[str, Any]:
        ...
