# LiteBot

LiteBot is a Python trading bot project focused on the `bot_v2` strategy engine.
This repository currently tracks the V2 module, runners, and supporting tests.

## Current Scope

- Main strategy package: `bot_v2/`
- Runner scripts:
	- `run_bot_v2.py` (single daily cycle)
	- `run_bot_v2_continuous.py` (continuous scheduler mode)
- Core dependencies: `requirements.txt`

## Requirements

- Python 3.11+
- Alpaca paper or live account credentials
- Linux/macOS shell (examples assume bash)

## Quick Start

1. Create and activate a virtual environment.

```bash
python3 -m venv litebotx_env
source litebotx_env/bin/activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`.

```env
APCA_API_KEY_ID=your_key
APCA_API_SECRET_KEY=your_secret
APCA_API_BASE_URL=https://paper-api.alpaca.markets
```

4. Run the V2 launcher.

```bash
python3 bot_v2/launcher.py
```

## Alternative Run Modes

- Single cycle run:

```bash
python3 run_bot_v2.py
```

- Continuous operation mode:

```bash
python3 run_bot_v2_continuous.py
```

## Logs and Output

- Runtime logs are written under `logs/`
- Daily summary JSON files are generated as `logs/daily_summary_YYYYMMDD.json`
- Supporting stats are stored in `bot_v2/data/`

## Testing

Run the targeted V2 observability test:

```bash
pytest -q tests/bot_v2/test_phase_a_observability.py
```

You can also run broader V2 tests from `bot_v2/tests/` and `tests/bot_v2/`.

## Notes

- Keep secrets in `.env` only; never commit credentials.
- Use Alpaca paper mode first before any live deployment.
