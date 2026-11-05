"""Pluggable football data providers.

Every provider converts its source format into the validated, provider-agnostic
records defined in :mod:`football_ai.providers.base`. The ingestion service then
persists them with full provenance. Providers never fabricate missing values:
anything the source does not supply stays ``None``.
"""
