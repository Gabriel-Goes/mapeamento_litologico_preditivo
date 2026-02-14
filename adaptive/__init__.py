"""Adaptive (CAS) pipeline scaffolding.

This package is the new, clean entrypoint for the "complex adaptive system"
loop (ingest -> dataset snapshot -> train -> predict -> store -> compare).

It is intentionally separated from legacy `codes/*` scripts so we can evolve a
stable API without refactoring everything at once.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
