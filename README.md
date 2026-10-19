# Slider-neuralnetwork

Template project for collecting slider-style captcha samples (authorized/test site), training a regression neural network, and providing a local prediction service. Includes Tampermonkey collection and automation scripts, a FastAPI collector and model server, and a PyTorch training script.

IMPORTANT: Use only on sites you own or explicitly have permission to test. Obtain user consent before uploading samples.

## Structure

- scripts/
  - tmm_collect.user.js  # Tampermonkey script to collect labeled samples when users submit
  - tmm_auto.user.js     # Tampermonkey script to call local model and attempt auto-solve (test-only)
  - train.py             # PyTorch training script
- server/
  - collector_server.py  # FastAPI collector that writes JSONL and saves images
  - model_server.py      # FastAPI model server that loads exported TorchScript model
  - models/              # model artifacts (gitignored)
- data/collected/        # collected samples (gitignored)
- notebooks/             # optional analysis notebooks
- README.md
- requirements.txt
- .gitignore

## Quickstart (local)

1. Create and activate a Python virtualenv:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Start the collector server (saves samples to `data/collected/samples.jsonl`):

   ```bash
   uvicorn server.collector_server:app --reload --port 8000
   ```

3. Install `scripts/tmm_collect.user.js` in Tampermonkey and set `@match` to your test domain (e.g. `http://localhost:5000/*`).

4. Manually complete the slider on your test page and submit. Confirm upload when prompted. Collected samples appear in `data/collected`.

5. Train a model (after collecting enough samples):

   ```bash
   python scripts/train.py --jsonl data/collected/samples.jsonl --out server/models/best.pth --export server/models/model.pt --epochs 20
   ```

6. Start the model server:

   ```bash
   uvicorn server.model_server:app --reload --port 9000
   ```

7. Install `scripts/tmm_auto.user.js` to test auto-solve in your authorized test environment.
