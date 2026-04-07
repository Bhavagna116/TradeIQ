"""
services/data_collection.py
----------------------------
Responsible for gathering recent market data and news about a given sector.

Strategy (in priority order):
  1. DuckDuckGo Instant-Answer API (no API key needed, free).
  2. Fallback to curated mock data if the external call times out or fails.

The module exposes a single public coroutine:
    fetch_sector_data(sector: str) -> dict
"""

import asyncio
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (override via environment variables)
# ---------------------------------------------------------------------------
DDGO_TIMEOUT = float(os.getenv("DDGO_TIMEOUT_SECONDS", "8"))   # seconds
DDGO_BASE_URL = "https://api.duckduckgo.com/"


# ---------------------------------------------------------------------------
# Curated mock data used when the live API call fails
# ---------------------------------------------------------------------------
MOCK_DATA: dict[str, dict[str, Any]] = {
    "pharmaceuticals": {
        "summary": (
            "India's pharmaceutical sector is the world's largest provider of generic medicines, "
            "supplying over 50 % of global vaccine demand and 25 % of all medicines by volume. "
            "The sector is forecasted to reach USD 130 billion by 2030, driven by biosimilars, "
            "API exports, and a growing domestic formulations market."
        ),
        "key_points": [
            "CDSCO regulatory approvals for 350+ new drugs in 2024",
            "API self-reliance push — PLI scheme disbursed ₹4 200 Cr to 55 units",
            "India-US trade corridor remains top export route (31 % share)",
            "Generic biologics & biosimilars pipeline growing at 18 % CAGR",
            "Digital health & AI drug-discovery investments crossing ₹2 000 Cr",
        ],
        "recent_news": [
            "Sun Pharma acquires Checkpoint Therapeutics for oncology pipeline expansion.",
            "Cipla receives USFDA approval for generic Spiriva Respimat inhaler.",
            "Dr. Reddy's reports 22 % YoY growth in North America generics.",
            "Union Budget 2025 allocates ₹2 500 Cr under PLI for API manufacturing.",
            "Serum Institute sets production target of 2 billion vaccine doses for FY26.",
        ],
    },
    "technology": {
        "summary": (
            "India's technology sector contributes ~10 % of GDP and employs 5.4 million "
            "professionals. IT services exports crossed USD 250 billion in FY25. "
            "AI, cloud, and cybersecurity are the fastest-growing verticals."
        ),
        "key_points": [
            "Generative-AI adoption in enterprise workflows up 3× YoY",
            "GCC (Global Capability Centre) count reaches 1 700 — fastest growing globally",
            "Startup funding recovered 40 % in H2-FY25 after 2023 winter",
            "India's SaaS market expected to hit USD 50 billion by 2030",
            "CERT-In mandates 6-hour breach reporting — cybersecurity budgets swelling",
        ],
        "recent_news": [
            "Infosys signs USD 2 billion AI-transformation deal with a European bank.",
            "TCS launches Pace Port in Chennai — 5 000 AI engineers to be trained.",
            "NASSCOM reports 15 % growth in digital engineering services.",
            "Reliance Jio's True5G subscriber base crosses 100 million.",
            "India ranked #3 globally in AI talent concentration (Stanford AI Index 2025).",
        ],
    },
    "agriculture": {
        "summary": (
            "Agriculture employs ~46 % of India's workforce and contributes 18 % to GDP. "
            "Agri-tech adoption, precision farming, and direct-to-market platforms are "
            "reshaping the sector toward higher productivity and reduced wastage."
        ),
        "key_points": [
            "PM-KISAN beneficiaries cross 110 million farmers",
            "Agri-tech startups raised USD 1.2 billion in FY25",
            "Drone-based crop monitoring deployed on 2 million hectares",
            "Food processing FDI inflows hit a 10-year high at USD 3.1 billion",
            "Organic exports grew 28 % — EU and USA leading destinations",
        ],
        "recent_news": [
            "Government raises MSP for Kharif crops by 7 % across 14 commodities.",
            "NABARD launches ₹10 000 Cr fund for agri infrastructure in aspirational districts.",
            "Ninjacart expands cold-chain network to 200 cities.",
            "India signs agri-trade MoU with UAE covering dates, spices, and pulses.",
            "Bayer and IARI collaborate on drought-tolerant wheat varieties for Indo-Gangetic plains.",
        ],
    },
}

# Default fallback for unknown sectors
_DEFAULT_MOCK: dict[str, Any] = {
    "summary": (
        "This sector is experiencing steady growth driven by government policy support, "
        "private investment, and digital transformation. Key players are consolidating "
        "market positions while creating opportunities for new entrants."
    ),
    "key_points": [
        "Sector revenue projected to grow at 12–15 % CAGR over the next five years",
        "Government PLI / incentive scheme disbursements on track",
        "FDI inflows increased 20 % YoY in the most recent fiscal year",
        "ESG compliance becoming a competitive differentiator for listed companies",
        "Digital adoption accelerating across supply chains and customer touchpoints",
    ],
    "recent_news": [
        "Industry body reports 18 % improvement in capacity utilisation.",
        "SEBI tightens disclosure norms — analysts expect improved price discovery.",
        "RBI keeps repo rate steady, providing relief to capital-intensive sub-sectors.",
        "Budget 2025 raises allocation for sector-specific infrastructure by ₹8 000 Cr.",
        "Global supply-chain realignment continues to benefit Indian exporters.",
    ],
}


from typing import Optional

# ---------------------------------------------------------------------------
# DuckDuckGo Instant-Answer helper
# ---------------------------------------------------------------------------
async def _fetch_duckduckgo(query: str) -> Optional[dict[str, Any]]:
    """
    Hits the DuckDuckGo Instant-Answer API and returns a simplified dict
    with 'summary' and 'related_topics'. Returns None on any failure.
    """
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=DDGO_TIMEOUT) as client:
            resp = await client.get(DDGO_BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        abstract = data.get("AbstractText", "").strip()
        related = [
            t.get("Text", "")
            for t in data.get("RelatedTopics", [])[:5]
            if isinstance(t, dict) and t.get("Text")
        ]

        if not abstract and not related:
            logger.info("DuckDuckGo returned empty result for query='%s'", query)
            return None

        return {"summary": abstract or "No abstract available.", "key_points": related}

    except (httpx.TimeoutException, httpx.HTTPStatusError, Exception) as exc:
        logger.warning("DuckDuckGo fetch failed (%s): %s", type(exc).__name__, exc)
        return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
async def fetch_sector_data(sector: str) -> dict[str, Any]:
    """
    Fetches market intelligence for the given sector.

    1. Tries DuckDuckGo Instant-Answer API for a live summary.
    2. Falls back to curated in-memory mock data.

    Returns a dict with at least:
        - 'summary'     : str   — a short paragraph about the sector
        - 'key_points'  : list  — bullet-point highlights
        - 'recent_news' : list  — recent news headlines (from mock if DDG used)
    """
    query = f"{sector} sector India stock market trade opportunities 2025"
    logger.info("Fetching sector data for '%s' …", sector)

    # Try live data first
    live_data = await _fetch_duckduckgo(query)

    # Merge live data with mock recent_news (DDG doesn't supply news headlines)
    mock = MOCK_DATA.get(sector, _DEFAULT_MOCK)

    if live_data and live_data.get("summary"):
        logger.info("Using live DuckDuckGo data for '%s'", sector)
        return {
            "summary": live_data["summary"],
            "key_points": live_data.get("key_points") or mock["key_points"],
            "recent_news": mock.get("recent_news", _DEFAULT_MOCK["recent_news"]),
        }

    # Fallback to fully mocked data
    logger.info("Using mock data for sector='%s'", sector)
    return mock
