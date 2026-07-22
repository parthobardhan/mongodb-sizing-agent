# MongoDB Sizing Agent — agent workflow

## Phases

1. **Intake** — Validate `intake.json` (useCaseName, queryLatencySlaMs, optional `productionRowCounts`, `dataModelingNotes`); read `schema.sql`, `indexes.sql`, ERD images. Ask when embed vs reference, hot paths, or keys are unclear.
2. **Model** — Write `cases/{useCase}/outputs/data-model.md` with disposition table, mapping, samples, index strategy, **Rationale**, **Assumptions**, approval block (`pending`).
3. **Sizing gate** — Write `cases/{useCase}/outputs/sizing_inputs.json` (agent-generated only): `productionDocumentCount` per top-level collection; `avgCardinality` for embedded (derive from `intake.json` `productionRowCounts` when possible).
4. **Approval** — User says `approve`; set status to `approved` in `data-model.md`. **Do not** write `seed.py`, start Docker, or run sizing before approval.
5. **Generate** — `seed.py` (500 docs per top-level collection), `mongodb_indexes.json` (no redundant compound prefixes).
6. **Tools** — `run_local_stack.sh` → seed → `apply_indexes.py` → `size_from_dbstats.py` → optional repository pytest → optional cleanup.
7. **Legacy migration** (post-approval, when `inputs/legacy/*` exists) — `mongo_repository.py` (PyMongo, method-for-method from legacy DAO) and `test_mongo_repository.py`; tools pipeline runs pytest against seeded local Mongo when present.

## Gates

- Missing anchor production count → ask (or document assumption in Assumptions); prefer `intake.json` `productionRowCounts`.
- Embedded cardinality: prefer `childCount / parentCount` from `productionRowCounts` when both known.
- Never invent production row counts silently.

## Index generation

Emit **one** compound index per relational composite; do not also emit prefix-only indexes on the same fields/options. Document prefix coverage in `data-model.md`.

## Deterministic numbers

Atlas Disk/RAM come **only** from `scripts/size_from_dbstats.py` (dbStats scaling). Per-collection collStats rows are report detail, not summed for Disk/RAM.

## SDK

- Local runtime: `LocalAgentOptions(cwd=project_root, setting_sources=["project", "plugins"])`
- `mode="plan"` until approval; `SendOptions(mode="agent")` for implementation
- Persist `agent_id` in `outputs/session.json` for `--resume`

## Cursor Cloud specific instructions

Python deps live in a virtualenv at `.venv` (the update script runs `python3 -m venv .venv` + `pip install -r requirements.txt`). Always invoke tools via `.venv/bin/python` / `.venv/bin/python -m pytest`. `requirements.txt` is the superset to install (it adds `fastapi`/`uvicorn`/`httpx`/`slack-bolt` for the dashboard/Slack integrations on top of `pyproject.toml` core deps).

Docker is installed but there is no systemd, so the daemon does NOT auto-start each session. Before any Mongo/integration work, start it manually and open the socket (user `ubuntu` is in the `docker` group):

```bash
sudo dockerd >/tmp/dockerd.log 2>&1 &
sleep 8 && sudo chmod 666 /var/run/docker.sock
```

Docker uses the `fuse-overlayfs` storage driver (set in `/etc/docker/daemon.json`) because the host kernel lacks full overlay2 support. Then start MongoDB with `bash scripts/run_local_stack.sh` (docker compose, `mongo:8` on 27017).

Run/test commands (see README "Tests" and "Workflow" for the full list):
- Hello-world / full E2E without any API key: `.venv/bin/python run_agent.py --case _example --phase tools-only --no-cleanup` (needs Docker+Mongo running).
- Unit + wiring: `.venv/bin/python -m pytest -m "not integration and not agent"` (no Docker/API key).
- Integration: `.venv/bin/python -m pytest -m integration` (needs Docker+Mongo).
- Dashboard (optional, fail-safe): `.venv/bin/python -m dashboard.server --case _example --port 8765` → http://localhost:8765.
- Slack bot (optional, local): `bash scripts/run_slack_bot.sh` (requires `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_CHANNEL_ID` in `.env`).

Notes:
- Interactive agent mode and `pytest -m agent` require `CURSOR_API_KEY` (not set in this environment); the `_example` case ships pre-built approved artifacts so the tools pipeline and integration tests run without it.
- There is no linter configured (no ruff/flake8/black/mypy config); "lint" is not a defined step here.
- Running the tools pipeline rewrites the committed `cases/_example/outputs/sizing-report.json` with environment-dependent numbers; revert it with `git checkout -- cases/_example/outputs/sizing-report.json` to keep the tree clean.
