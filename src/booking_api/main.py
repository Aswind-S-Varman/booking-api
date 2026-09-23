from fastapi import FastAPI

app = FastAPI(
    title="Booking API",
    description="Book shared resources without double-booking them.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


