"""LumenAI research namespace — ISOLATED from the production FastAPI app.

Nothing under ``app`` imports anything from ``research``. This package holds
research-only computer-vision experiments (Project Lens Stage 5). It reuses the
production GOVERNANCE contracts (provenance classes, leakage-safe splitting, the
governed observation taxonomy) by importing them read-only, but it never changes
clinical decisioning, inference, promotion, or deployment.

Heavy ML dependencies (PyTorch, etc.) are OPTIONAL and live in
``backend/requirements-research.txt`` — they are NOT part of the production
image or CI, so every module here must import cleanly without them.
"""
