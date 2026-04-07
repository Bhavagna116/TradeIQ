import httpx, time

print("=== LIVE GEMINI API TEST ===")

start = time.time()
r = httpx.get(
    "http://localhost:8000/analyze/technology",
    headers={"X-API-Key": "dev-key-12345"},
    timeout=60,
)
elapsed = round(time.time() - start, 2)
data = r.json()

report = data.get("report", "")

print("HTTP Status :", r.status_code)
print("Sector      :", data.get("sector"))
print("Response time:", elapsed, "s")
print("Report length:", len(report), "chars")
print("Generated at :", data.get("generated_at"))
print()

# Check if Gemini generated (not mock) by looking for Gemini-specific phrasing
is_gemini = "mock" not in report.lower()[:200] and len(report) > 800
print("AI Source   :", "LIVE GEMINI" if is_gemini else "MOCK FALLBACK")
print()

# Print first 600 chars safely
safe_preview = report[:600].encode("ascii", errors="replace").decode("ascii")
print("--- REPORT PREVIEW ---")
print(safe_preview)
