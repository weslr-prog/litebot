#!/usr/bin/env python3
"""
Test PreFilter with Enhanced Logging
Shows detailed output for each filter stage
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from bot_v2.core.pre_filter import PreFilter
from bot_v2.config.prefilter_config import SIMPLE_PREFILTER_CONFIG
from data_loader import DataLoader
import json

print("="*80)
print("🧪 Testing PreFilter with Enhanced Logging")
print("="*80)
print()

# Load universe
universe_file = Path(__file__).parent / "bot_v2/data/mid_cap_universe.json"
with open(universe_file) as f:
    data = json.load(f)

all_stocks = []
for sector in ["technology", "consumer_discretionary", "healthcare_biotech",
               "financials", "energy_clean", "industrials", 
               "communication", "materials_commodities"]:
    all_stocks.extend(data.get(sector, []))

print(f"📊 Input Universe: {len(all_stocks)} stocks")
print(f"   Sectors: 8 (tech, consumer, healthcare, financials, energy, industrials, comm, materials)")
print()

# Initialize PreFilter
data_loader = DataLoader()
prefilter = PreFilter(data_loader, SIMPLE_PREFILTER_CONFIG)

# Run filter
candidates = prefilter.run_filter(all_stocks)

print()
print("="*80)
print(f"✅ TEST COMPLETE")
print(f"   Final Candidates: {len(candidates)} stocks")
print(f"   Expected Range: 20-40 stocks")
print(f"   Status: {'✅ PASS' if 20 <= len(candidates) <= 40 else '⚠️ OUT OF RANGE'}")
print("="*80)
