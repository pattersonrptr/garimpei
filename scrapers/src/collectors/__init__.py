"""Offer collectors: ask a store for a product by its identifier (ISBN now,
EAN/GTIN later) and send plain offers to the backend.

The core (``offers``, ``ports``, ``use_cases``) knows no HTTP library. Store
adapters live in ``stores``; wiring happens only in ``run``.
"""
