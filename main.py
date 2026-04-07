"""
main.py
-------
FastAPI application entry point.
Defines the /analyze/{sector} endpoint with authentication,
rate limiting, input validation, and Swagger documentation.
"""

# Load .env FIRST — before any module reads os.getenv()
from dotenv import load_dotenv
load_dotenv()

import logging
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services.ai_analysis import generate_analysis_report
from services.data_collection import fetch_sector_data
from utils.auth import verify_api_key
from utils.rate_limiter import RateLimiter
from utils.email_sender import send_markdown_email

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory rate limiter (singleton, lives for the process lifetime)
# ---------------------------------------------------------------------------
rate_limiter = RateLimiter(max_requests=5, window_seconds=60)


# ---------------------------------------------------------------------------
# App lifespan (startup / shutdown hooks)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Trade Opportunities API is starting up …")
    yield
    logger.info("🛑 Trade Opportunities API is shutting down …")


# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Trade Opportunities API",
    description=(
        "A FastAPI service that analyses Indian market data for a given sector "
        "and returns structured trade-opportunity insights as a Markdown report."
    ),
    version="1.0.0",
    contact={"name": "Senior Dev", "email": "dev@example.com"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------
import base64

class AnalysisResponse(BaseModel):
    sector: str
    report: str
    generated_at: str

    model_config = {"json_schema_extra": {
        "example": {
            "sector": "pharmaceuticals",
            "report": "# Pharmaceuticals Sector Analysis\n\n## Overview\n...",
            "generated_at": "2026-04-07T17:00:00",
        }
    }}

class EmailRequest(BaseModel):
    email: str
    sector: str
    report: str
    pdf_base64: str = None

@app.post("/api/send_email")
async def email_report(req: EmailRequest):
    """Dispatches the generated report to the specified email."""
    pdf_bytes = base64.b64decode(req.pdf_base64) if req.pdf_base64 else None
    success = send_markdown_email(
        to_email=req.email,
        subject=f"TradeIQ Intelligence: {req.sector.title()} Sector",
        markdown_content=req.report,
        pdf_filename=f"TradeIQ_{req.sector.title()}.pdf",
        pdf_bytes=pdf_bytes
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email.")
    return {"status": "success", "message": "Email sent"}


# ---------------------------------------------------------------------------
# Serve static files (frontend)
# ---------------------------------------------------------------------------
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the interactive frontend HTML page."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Trade Opportunities API is running. See /docs for API reference."}


# ---------------------------------------------------------------------------
# Health-check endpoint (no auth required)
# ---------------------------------------------------------------------------
@app.get(
    "/health",
    summary="Health Check",
    tags=["System"],
)
async def health_check():
    """Returns a simple alive signal. Useful for load-balancer probes."""
    return {"status": "ok", "service": "Trade Opportunities API"}


# ---------------------------------------------------------------------------
# Core endpoint
# ---------------------------------------------------------------------------
@app.get(
    "/analyze/{sector}",
    response_model=AnalysisResponse,
    summary="Analyse an Indian market sector",
    tags=["Analysis"],
    responses={
        200: {"description": "Markdown analysis report"},
        400: {"description": "Invalid sector name"},
        401: {"description": "Missing or invalid API key"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
async def analyze_sector(
    sector: str,
    request: Request,
    x_api_key: str = Header(..., description="Your API key (X-API-Key header)"),
):
    """
    **Analyse trade opportunities for a given Indian market sector.**

    - Validates the sector name (letters only, 2-50 chars)
    - Authenticates the caller via `X-API-Key` header
    - Enforces per-key rate limiting (max 5 req / 60 s)
    - Fetches recent market data / news for the sector
    - Uses the Gemini LLM to generate a structured Markdown report
    """

    # ── 1. Authentication ────────────────────────────────────────────────
    verify_api_key(x_api_key)          # raises 401 if invalid
    identifier = x_api_key            # use API key as the session identifier

    # ── 2. Rate limiting ─────────────────────────────────────────────────
    allowed, retry_after = rate_limiter.check(identifier)
    if not allowed:
        logger.warning("Rate limit exceeded for key=%s", identifier[:8] + "…")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {retry_after} second(s).",
        )

    # ── 3. Input validation ───────────────────────────────────────────────
    sector_clean = sector.strip().lower()
    if not sector_clean:
        raise HTTPException(status_code=400, detail="Sector name must not be empty.")
    if not re.fullmatch(r"[a-zA-Z\s]{2,50}", sector_clean):
        raise HTTPException(
            status_code=400,
            detail=(
                "Sector name must contain only alphabetic characters "
                "and spaces (2–50 chars)."
            ),
        )

    logger.info(
        "Sector analysis requested: sector=%s  key=%s",
        sector_clean,
        identifier[:8] + "…",
    )

    # ── 4. Data collection ────────────────────────────────────────────────
    try:
        raw_data = await fetch_sector_data(sector_clean)
    except Exception as exc:
        logger.error("Data collection failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch market data. Please try again later.",
        )

    # ── 5. AI analysis ────────────────────────────────────────────────────
    try:
        report_md = await generate_analysis_report(sector_clean, raw_data)
    except Exception as exc:
        logger.error("AI analysis failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate analysis. Please try again later.",
        )

    generated_at = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    logger.info("Analysis complete for sector=%s", sector_clean)

    return AnalysisResponse(
        sector=sector_clean,
        report=report_md,
        generated_at=generated_at,
    )


# ---------------------------------------------------------------------------
# Global exception handler (catch-all)
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )
