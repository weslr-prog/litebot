import os
import csv
from datetime import datetime

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def append_csv(path: str, fieldnames: list[str], row: dict):
    ensure_dir(os.path.dirname(path))
    file_exists = os.path.isfile(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            w.writeheader()
        w.writerow(row | {"timestamp": datetime.utcnow().isoformat()})

def log_event(event_type, data):
    """
    Simple event logger.
    """
    print(f"[EVENT] {event_type}: {data}")


def log_error(module, error_type, message, level="ERROR"):
    """
    Simple error logger.
    """
    print(f"[{level}] {module}::{error_type}: {message}")


def log_missing_bars(symbol: str, timeframe: str, start: str, end: str, expected: int | None, got: int, notes: str | None = None, provider: str | None = None, out_path: str = "logs/missing_bars.csv"):
    """
    Append a row to a CSV capturing data gaps so you can monitor provider issues.
    """
    fieldnames = [
        "timestamp",
    "provider",
        "symbol",
        "timeframe",
        "start",
        "end",
        "expected",
        "got",
        "notes",
    ]
    row = {
    "provider": provider or "",
        "symbol": symbol,
        "timeframe": timeframe,
        "start": start,
        "end": end,
        "expected": expected if expected is not None else "",
        "got": got,
        "notes": notes or "",
    }
    append_csv(out_path, fieldnames, row)


def summarize_missing_bars(out_path: str = "logs/missing_bars.csv") -> dict:
    """
    Aggregate missing-bars CSV into a simple health report by provider and symbol.
    Returns a dict with provider-level totals and top offending symbols.
    """
    if not os.path.isfile(out_path):
        return {"providers": {}, "top_symbols": []}
    import csv
    from collections import defaultdict, Counter
    providers = defaultdict(int)
    symbol_counts = Counter()
    with open(out_path, "r", newline="") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            prov = row.get("provider") or "unknown"
            providers[prov] += 1
            sym = row.get("symbol") or ""
            if sym:
                symbol_counts[sym] += 1
    top_syms = symbol_counts.most_common(20)
    return {"providers": dict(providers), "top_symbols": top_syms}
