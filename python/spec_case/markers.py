"""The four co-location markers, as no-op decorators.

They only *mark* functions for specgen's static extraction; at runtime each
returns the function unchanged, so importing and annotating costs nothing and
never changes behavior. specgen reads them with `ast` (it never runs the code),
so the no-op bodies are irrelevant — extraction is purely syntactic.

Grammar: ../../languages/python.md. Meaning of each: ../../docs/concepts.md.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def _identity(fn: F) -> F:
    return fn


def spec(text: str) -> Callable[[F], F]:
    """The function's contract preamble (0..1), shared by all its cases."""
    return _identity


def case(
    id: str,
    desc: str,
    *,
    input: str = "",
    expect: str = "",
    forbid: str = "",
    group: str | None = None,
) -> Callable[[F], F]:
    """A concrete scenario to verify (0..N). `id` matches ^[a-z][a-z0-9_]*$."""
    return _identity


def link(ref: str) -> Callable[[F], F]:
    """A curated "see also" (0..N): a repo-relative md path, or a symbol-id."""
    return _identity


def rule(text: str) -> Callable[[F], F]:
    """Review criteria (0..N): what to watch for. On a function it's a per-function
    criterion; on a class it's a type-wide usage constraint (e.g. "per-request
    only — do not cache/reuse"), surfaced when a diff references the type."""
    return _identity
