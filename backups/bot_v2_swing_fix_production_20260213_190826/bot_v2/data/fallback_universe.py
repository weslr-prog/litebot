"""
Fallback Universe - Curated list of mid-cap stocks for fallback screening

STRICT MID-CAP CRITERIA:
- Market Cap: $2B - $15B (true mid-cap range)
- Average Daily Volume: >500K shares
- No mega-caps (>$50B) or micro-caps (<$1B)
- No blacklisted symbols (NI, OGE, T, JD, TU, VIRT, BXMT, VIPS)

Last Updated: January 13, 2026
CLEANED: Removed mega-caps, duplicates, and non-qualifying stocks
"""
from typing import List, Dict


# Curated Mid-Cap Universe (Market Cap $2B-$15B range ONLY)
# Total: ~120 true mid-cap stocks
#
# These stocks are selected for:
# - Consistent trading volume (>500K daily)
# - TRUE mid-cap market cap range ($2B-$15B)
# - Sector diversification
# - Suitable volatility for D+1 trading
#
# EXCLUDED from this list:
# - Mega-caps: AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, META, etc.
# - Large-caps >$50B: NFLX, DIS, PYPL, SQ, etc.
# - Micro-caps <$1B: WISH, ACB, ASTR, etc.
# - Blacklisted: NI, OGE, T, JD, TU, VIRT, BXMT, VIPS

MID_CAP_FALLBACK = [
    # ═══════════════════════════════════════════════════════════════
    # AIRLINES & TRAVEL - High volatility, momentum plays
    # ═══════════════════════════════════════════════════════════════
    "AAL",      # American Airlines (~$8-9B)
    "ALK",      # Alaska Air (~$5-6B)
    "JBLU",     # JetBlue (~$2-3B)
    "NCLH",     # Norwegian Cruise (~$8B)
    "H",        # Hyatt (~$12B)
    
    # ═══════════════════════════════════════════════════════════════
    # RESTAURANTS & CONSUMER - Gap & Go candidates
    # ═══════════════════════════════════════════════════════════════
    "CAKE",     # Cheesecake Factory (~$2-3B)
    "TXRH",     # Texas Roadhouse (~$8-10B)
    "EAT",      # Brinker International (~$3B)
    "BLMN",     # Bloomin' Brands (~$2B)
    "WING",     # Wingstop (~$10B)
    
    # ═══════════════════════════════════════════════════════════════
    # RETAIL - Earnings momentum
    # ═══════════════════════════════════════════════════════════════
    "DKS",      # Dick's Sporting Goods (~$14B)
    "FIVE",     # Five Below (~$6-8B)
    "BOOT",     # Boot Barn (~$3-4B)
    "OLLI",     # Ollie's Bargain (~$3B)
    "GPS",      # Gap Inc (~$8B)
    "ANF",      # Abercrombie (~$7B)
    "AEO",      # American Eagle (~$4B)
    "URBN",     # Urban Outfitters (~$4B)
    "BURL",     # Burlington (~$15B)
    "RH",       # RH/Restoration Hardware (~$8B)
    "GME",      # GameStop (~$10B)
    "CHWY",     # Chewy (~$12B)
    
    # ═══════════════════════════════════════════════════════════════
    # ENERGY - High beta, momentum (true mid-caps only)
    # ═══════════════════════════════════════════════════════════════
    "RIG",      # Transocean (~$3-4B)
    "SWN",      # Southwestern Energy (~$6-7B)
    "AR",       # Antero Resources (~$6-8B)
    "RRC",      # Range Resources (~$6-7B)
    "APA",      # APA Corporation (~$10B)
    "OVV",      # Ovintiv (~$10B)
    
    # ═══════════════════════════════════════════════════════════════
    # CLEAN ENERGY / EV - Volatility & momentum
    # ═══════════════════════════════════════════════════════════════
    "PLUG",     # Plug Power (~$2-3B)
    "SEDG",     # SolarEdge (~$2-3B)
    "RUN",      # Sunrun (~$3B)
    "LCID",     # Lucid Motors (~$8B)
    "RIVN",     # Rivian (~$12-15B)
    "NIO",      # NIO (~$10B)
    "XPEV",     # XPeng (~$8B)
    
    # ═══════════════════════════════════════════════════════════════
    # SOFTWARE & CLOUD - True mid-caps
    # ═══════════════════════════════════════════════════════════════
    "CFLT",     # Confluent (~$10B)
    "ESTC",     # Elastic (~$10B)
    "PATH",     # UiPath (~$10B)
    "DOCN",     # DigitalOcean (~$3B)
    "GTLB",     # GitLab (~$8B)
    "S",        # SentinelOne (~$7B)
    "TENB",     # Tenable (~$5B)
    "FRSH",     # Freshworks (~$5B)
    "ASAN",     # Asana (~$3B)
    "OKTA",     # Okta (~$15B)
    
    # ═══════════════════════════════════════════════════════════════
    # SEMICONDUCTORS - True mid-caps
    # ═══════════════════════════════════════════════════════════════
    "SWKS",     # Skyworks (~$15B)
    "QRVO",     # Qorvo (~$8B)
    "SLAB",     # Silicon Labs (~$5B)
    "WOLF",     # Wolfspeed (~$3B)
    
    # ═══════════════════════════════════════════════════════════════
    # HEALTHCARE/BIOTECH - Event-driven volatility
    # ═══════════════════════════════════════════════════════════════
    "INCY",     # Incyte (~$12B)
    "VTRS",     # Viatris (~$11B)
    "BMRN",     # BioMarin (~$15B)
    "EXAS",     # Exact Sciences (~$10B)
    "SRPT",     # Sarepta (~$10B)
    "NTLA",     # Intellia (~$2B) - CRISPR
    "CRSP",     # CRISPR Therapeutics (~$4B)
    "BEAM",     # Beam Therapeutics (~$2B)
    "IONS",     # Ionis (~$8B)
    "ARWR",     # Arrowhead (~$5B)
    "RARE",     # Ultragenyx (~$3B)
    
    # Health Insurance & Services
    "OSCR",     # Oscar Health (~$3B)
    "HIMS",     # Hims & Hers (~$3B)
    "TDOC",     # Teladoc (~$3B)
    
    # ═══════════════════════════════════════════════════════════════
    # INDUSTRIAL - Cyclical momentum
    # ═══════════════════════════════════════════════════════════════
    "CLF",      # Cleveland-Cliffs (~$6-8B)
    "X",        # US Steel (~$7-8B)
    "AA",       # Alcoa (~$6-8B)
    "MP",       # MP Materials (~$3B)
    "LAC",      # Lithium Americas (~$2B)
    "LTHM",     # Livent (~$4B)
    
    # ═══════════════════════════════════════════════════════════════
    # MEDIA/ENTERTAINMENT - Volatility on news
    # ═══════════════════════════════════════════════════════════════
    "PARA",     # Paramount (~$7-9B)
    "FOXA",     # Fox Corp (~$15B)
    "SIRI",     # SiriusXM (~$15B)
    
    # ═══════════════════════════════════════════════════════════════
    # REAL ESTATE/HOUSING - Interest rate sensitive
    # ═══════════════════════════════════════════════════════════════
    "Z",        # Zillow (~$10-12B)
    "COMP",     # Compass (~$2B)
    "TOL",      # Toll Brothers (~$10B)
    "MTH",      # Meritage Homes (~$8B)
    "KBH",      # KB Home (~$5B)
    "CCS",      # Century Communities (~$2B)
    
    # ═══════════════════════════════════════════════════════════════
    # FINANCIAL SERVICES - Fintech volatility
    # ═══════════════════════════════════════════════════════════════
    "HOOD",     # Robinhood (~$8-10B)
    "SOFI",     # SoFi (~$7-9B)
    "AFRM",     # Affirm (~$10-12B)
    "UPST",     # Upstart (~$3B)
    
    # Crypto Proxies (mid-cap)
    "MARA",     # Marathon Digital (~$5B)
    "RIOT",     # Riot Platforms (~$3B)
    "CLSK",     # CleanSpark (~$3B)
    
    # ═══════════════════════════════════════════════════════════════
    # SPACE & DEFENSE - Emerging mid-caps
    # ═══════════════════════════════════════════════════════════════
    "RKLB",     # Rocket Lab (~$6B)
    "ASTS",     # AST SpaceMobile (~$6B)
    "JOBY",     # Joby Aviation (~$4B)
    "ACHR",     # Archer Aviation (~$2B)
    
    # ═══════════════════════════════════════════════════════════════
    # HIGH-VOLATILITY MID-CAPS
    # ═══════════════════════════════════════════════════════════════
    "AMC",      # AMC Entertainment (~$2B)
    "BB",       # BlackBerry (~$2B)
    "PLTR",     # Palantir (~$15B - borderline)
]


# Sector-balanced diversified universe for more conservative fallback
# 40 stocks, 4-5 per sector
DIVERSIFIED_MID_CAP = [
    # Airlines/Travel (4)
    "AAL", "ALK", "JBLU", "NCLH",
    # Consumer/Restaurants (4)
    "CAKE", "TXRH", "DKS", "FIVE",
    # Energy (4)
    "SWN", "AR", "RIG", "APA",
    # Technology/SaaS (4)
    "CFLT", "DOCN", "GTLB", "S",
    # Healthcare/Biotech (5)
    "INCY", "VTRS", "NTLA", "OSCR", "CRSP",
    # Industrial (4)
    "CLF", "AA", "X", "MP",
    # Financial/Fintech (4)
    "HOOD", "SOFI", "AFRM", "UPST",
    # Media (3)
    "PARA", "SIRI", "FOXA",
    # Real Estate (4)
    "Z", "TOL", "KBH", "CCS",
    # Space (3)
    "RKLB", "ASTS", "JOBY",
    # EV/Clean Energy (4)
    "LCID", "RIVN", "NIO", "PLUG",
]


def get_fallback_universe(diversified: bool = False) -> List[str]:
    """
    Get the fallback universe of mid-cap stocks.
    
    Args:
        diversified: If True, return sector-balanced subset (~40 stocks)
                    If False, return full mid-cap list (~120 stocks)
    
    Returns:
        List of stock symbols (unique, no duplicates)
    """
    if diversified:
        return list(dict.fromkeys(DIVERSIFIED_MID_CAP))  # Remove dupes, preserve order
    return list(dict.fromkeys(MID_CAP_FALLBACK))  # Remove dupes, preserve order


def get_sector_stocks(sector: str) -> List[str]:
    """
    Get mid-cap stocks for a specific sector.
    
    Args:
        sector: Sector name (airlines, restaurants, energy, tech, etc.)
        
    Returns:
        List of stock symbols in that sector (mid-cap only)
    """
    # Only include TRUE mid-caps in sector mappings
    sector_map: Dict[str, List[str]] = {
        "airlines": ["AAL", "ALK", "JBLU", "NCLH"],
        "travel": ["NCLH", "H"],
        "restaurants": ["CAKE", "TXRH", "EAT", "BLMN", "WING"],
        "retail": ["DKS", "FIVE", "BOOT", "OLLI", "GPS", "ANF", "AEO", "URBN", "GME", "CHWY"],
        "energy": ["RIG", "SWN", "AR", "RRC", "APA", "OVV"],
        "cleanenergy": ["PLUG", "SEDG", "RUN"],
        "ev": ["LCID", "RIVN", "NIO", "XPEV"],
        "tech": ["CFLT", "ESTC", "PATH", "DOCN", "GTLB", "S", "TENB", "FRSH", "ASAN", "OKTA"],
        "semiconductors": ["SWKS", "QRVO", "SLAB", "WOLF"],
        "healthcare": ["INCY", "VTRS", "BMRN", "EXAS", "SRPT", "OSCR", "HIMS", "TDOC"],
        "biotech": ["NTLA", "CRSP", "BEAM", "IONS", "ARWR", "RARE"],
        "industrial": ["CLF", "X", "AA", "MP", "LAC", "LTHM"],
        "media": ["PARA", "FOXA", "SIRI"],
        "realestate": ["Z", "COMP", "TOL", "MTH", "KBH", "CCS"],
        "fintech": ["HOOD", "SOFI", "AFRM", "UPST"],
        "crypto": ["MARA", "RIOT", "CLSK"],
        "space": ["RKLB", "ASTS", "JOBY", "ACHR"],
        "highvol": ["AMC", "BB", "PLTR"],
    }
    
    return sector_map.get(sector.lower(), [])


def validate_universe() -> Dict[str, List[str]]:
    """
    Validate the universe against blacklist and report issues.
    
    Returns:
        Dict with 'valid', 'blacklisted', and 'duplicates' lists
    """
    from pathlib import Path
    import json
    
    # Load blacklist
    blacklist_path = Path(__file__).parent.parent / "config" / "symbol_blacklist.json"
    blacklisted_symbols = set()
    if blacklist_path.exists():
        with open(blacklist_path) as f:
            bl = json.load(f)
            blacklisted_symbols = set(bl.get("permanent", []))
    
    # Check for issues
    all_symbols = MID_CAP_FALLBACK.copy()
    seen = set()
    duplicates = []
    blacklisted_found = []
    valid = []
    
    for sym in all_symbols:
        if sym in seen:
            duplicates.append(sym)
        elif sym in blacklisted_symbols:
            blacklisted_found.append(sym)
        else:
            valid.append(sym)
            seen.add(sym)
    
    return {
        "valid": valid,
        "blacklisted": blacklisted_found,
        "duplicates": duplicates,
        "total_valid": len(valid)
    }
