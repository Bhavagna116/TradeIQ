"""
services/ai_analysis.py
------------------------
Generates a structured Markdown trade-opportunity report for a given sector
by calling the Google Gemini API.

If GEMINI_API_KEY is not configured (or the call fails), the module falls back
to a richly-templated mock report so the application always returns useful data.

Public interface:
    generate_analysis_report(sector: str, data: dict) -> str
"""

import asyncio
import logging
import os
import textwrap
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TIMEOUT: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))


# ---------------------------------------------------------------------------
# Gemini API caller (async, with timeout)
# ---------------------------------------------------------------------------
async def _call_gemini(prompt: str) -> Optional[str]:
    """
    Sends a prompt to the Gemini REST API and returns the generated text.
    Returns None if the API key is absent, the call times out, or an error occurs.
    """
    if not GEMINI_API_KEY:
        logger.info("GEMINI_API_KEY not set — skipping live Gemini call.")
        return None

    try:
        import httpx  # imported here so the module loads without httpx if not needed

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            },
        }

        async with httpx.AsyncClient(timeout=GEMINI_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

        # Extract the text from Gemini's response structure
        text = (
            result.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        if text:
            logger.info("Gemini API returned a valid response.")
            return text

        logger.warning("Gemini API returned an empty response body.")
        return None

    except asyncio.TimeoutError:
        logger.warning("Gemini API call timed out after %.1fs.", GEMINI_TIMEOUT)
        return None
    except Exception as exc:
        logger.error("Gemini API call failed (%s): %s", type(exc).__name__, exc)
        return None


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------
def _build_prompt(sector: str, data: dict[str, Any]) -> str:
    """
    Constructs the prompt sent to Gemini, embedding the collected sector data.
    """
    summary = data.get("summary", "No summary available.")
    key_points = "\n".join(f"- {p}" for p in data.get("key_points", []))
    recent_news = "\n".join(f"- {n}" for n in data.get("recent_news", []))

    return textwrap.dedent(f"""
        You are a senior financial analyst specialising in Indian equity markets.
        Analyse the following data about the **{sector.title()}** sector in India
        and produce a structured Markdown report that a retail investor or fund
        manager could act on.

        ## Collected Data

        ### Overview
        {summary}

        ### Key Points
        {key_points}

        ### Recent News
        {recent_news}

        ## Required Report Structure

        Return ONLY the Markdown report — no extra commentary.

        # {sector.title()} Sector — Trade Opportunities Analysis

        ## Overview
        (2–3 paragraphs covering sector background and current state in India)

        ## Key Trends
        (3–5 bullet points with explanation)

        ## Opportunities
        (3–5 specific, actionable trade opportunities for investors)

        ## Risks
        (3–5 key risks that investors should monitor)

        ## Conclusion
        (1–2 paragraphs — final recommendation / outlook)
    """).strip()


# ---------------------------------------------------------------------------
# Mock report generator (used when Gemini is unavailable)
# ---------------------------------------------------------------------------
def _generate_mock_report(sector: str, data: dict[str, Any]) -> str:
    """
    Returns a richly-formatted mock Markdown report built from the sector data.
    This ensures the API always returns a meaningful response.
    """
    summary = data.get("summary", "The sector is showing strong growth momentum.")
    key_points = data.get("key_points", [])
    recent_news = data.get("recent_news", [])
    today = time.strftime("%B %d, %Y", time.gmtime())
    sector_title = sector.title()

    kp_md = "\n".join(f"- **{p}**" for p in key_points) if key_points else "- Data unavailable"
    news_md = "\n".join(f"- {n}" for n in recent_news) if recent_news else "- No recent news available"

    return f"""# {sector_title} Sector — Trade Opportunities Analysis
*Report generated on {today} | Source: Trade Opportunities API*

---

## Overview

The **{sector_title}** sector remains one of India's most strategically significant
industries, playing a critical role in GDP contribution, employment generation, and
foreign-exchange earnings. {summary}

India's macroeconomic fundamentals — a young demographic, rising middle-class
consumption, and government-led infrastructure investment — continue to provide a
long-term structural tailwind for this sector. With increasing policy focus and
private-sector participation, the sector is well-positioned for sustained growth
over the next 3–5 years.

---

## Key Trends

{kp_md}

- **ESG & Sustainability**: Listed companies in the {sector_title} sector face growing
  pressure from institutional investors to publish credible ESG roadmaps, opening
  opportunities for early adopters.
- **Digital Transformation**: Technology adoption — AI, IoT, and data analytics —
  is compressing operating costs and improving decision-making speed across the value chain.

---

## Opportunities

- **Domestic Consumption Play**: Rising income levels and urbanisation are expanding
  the addressable market within India. Mid-cap companies with dominant regional
  positions may offer attractive risk-adjusted returns.
- **Export Expansion**: Geopolitical realignment (China+1 strategy) is redirecting
  global procurement toward India. Companies with certified export infrastructure
  stand to capture significant incremental revenue.
- **Government Incentive Schemes**: PLI (Production Linked Incentive) and other
  sector-specific schemes are de-risking large capital expenditure for incumbents
  and new entrants alike.
- **M&A and Consolidation**: Fragmented sub-sectors are ripe for consolidation.
  Acquirers with strong balance sheets can capture market share at attractive
  valuation multiples.
- **Listed Small & Mid Caps**: Several under-followed companies in the {sector_title}
  space trade at a discount to intrinsic value, providing a margin of safety for
  patient investors.

---

## Risks

- **Regulatory Changes**: Policy reversals or tightening of compliance norms (e.g.,
  pricing controls, environmental regulations) can crimp margins without warning.
- **Global Macro Headwinds**: A stronger USD, elevated commodity prices, or a global
  recessionary environment could dampen export demand and compress import-heavy cost
  structures.
- **Competitive Intensity**: Increased FDI and domestic new-entrant activity may erode
  pricing power for incumbents, especially in commoditised sub-segments.
- **Currency Risk**: Companies with significant USD-denominated debt or import exposure
  face earnings volatility when INR depreciates.
- **Concentration Risk**: Dependence on a small number of customers, suppliers, or
  geographies amplifies business risk; investors should scrutinise customer-concentration
  disclosures.

---

## Recent Market Developments

{news_md}

---

## Conclusion

The **{sector_title}** sector presents a compelling medium-to-long-term investment
opportunity within the Indian equity market. The combination of supportive government
policy, structural demand drivers, and improving operational efficiency creates
multiple paths to value creation for disciplined investors.

**Recommended approach**: Build positions in quality large-caps for stability, while
selectively accumulating fundamentally sound mid-caps that are direct beneficiaries
of the trends identified above. Maintain strict stop-losses to manage downside risk,
and review the thesis quarterly in light of regulatory and macro developments.

> ⚠️ *This report is generated for informational purposes only and does not constitute
> financial advice. Please consult a SEBI-registered investment advisor before making
> any investment decisions.*
"""


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
async def generate_analysis_report(sector: str, data: dict[str, Any]) -> str:
    """
    Generates a structured Markdown trade-opportunity report.

    1. Builds a detailed prompt incorporating the collected sector data.
    2. Calls the Gemini API (if key is configured).
    3. Falls back to the mock report if Gemini is unavailable or fails.

    Args:
        sector : Cleaned sector name (lowercase, alpha only).
        data   : Dict returned by fetch_sector_data().

    Returns:
        A Markdown-formatted string ready to be returned to the caller.
    """
    prompt = _build_prompt(sector, data)
    logger.info("Requesting AI analysis for sector='%s' …", sector)

    # Attempt live Gemini call
    gemini_result = await _call_gemini(prompt)

    if gemini_result:
        logger.info("Using Gemini-generated report for sector='%s'", sector)
        return gemini_result

    # Fallback
    logger.info("Using mock report for sector='%s'", sector)
    return _generate_mock_report(sector, data)
