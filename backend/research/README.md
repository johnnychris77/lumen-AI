# backend/research — isolated research code (NOT production)

Research-only experiments for Project Lens Stage 5. **Nothing in `app/` imports
this package.** Heavy ML dependencies are optional and separate
(`backend/requirements-research.txt`); CI and the production image do not install
them, and every module here imports cleanly without PyTorch.

- Design + governance: `docs/model-development/STAGE_5A_RESEARCH_FOUNDATION.md`
- CPU smoke tests use a deterministic stub embedder — no torch, no GPU, no weights.
- Never commit model weights, datasets, patient images, or secrets.

Run the research tests (no torch required):

```bash
cd backend && python -m pytest tests/test_stage5a_research_foundation.py -q
```

Set up an **isolated** research environment for the real DINOv2 path:

```bash
python -m venv .venv-research && . .venv-research/bin/activate
pip install -r backend/requirements.txt -r backend/requirements-research.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```
