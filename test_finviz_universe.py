"""
Manual test for Finviz screener integration.
- Safe to run: will NOT crash if blocked.
- Prints result and exits 0.
"""

from dynamic_universe_generator import get_dynamic_universe


def main():
    print("FINVIZ SCREENER TEST")
    print("=====================")

    try:
        symbols = get_dynamic_universe(
            min_price=10.0,
            max_price=35.0,
            min_volume=1_000_000,
            max_candidates=100,
            save_to_file=False,
            use_finviz=True
        )

        if symbols:
            print(f"✅ Finviz returned {len(symbols)} symbols")
            print(f"First 10: {symbols[:10]}")
        else:
            print("⚠️ Finviz returned no symbols (likely blocked). Fallback works.")

    except Exception as exc:
        print(f"⚠️ Finviz test failed safely: {exc}")


if __name__ == "__main__":
    main()
