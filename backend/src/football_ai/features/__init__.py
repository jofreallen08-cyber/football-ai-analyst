"""Deterministic football analytics (Pandas/NumPy).

All functions are pure: they take DataFrames and return plain dataclasses. Missing
statistics are never imputed — averages are computed only over matches where the
value exists, coverage is reported, and absent metrics are listed in ``missing``.
"""
