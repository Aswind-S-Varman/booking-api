from fastapi import FastAPI
from .routers import auth, resources, bookings

from .routers import auth

app = FastAPI(
    title="Booking API",
    description="Book shared resources without double-booking them.",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(resources.router)
app.include_router(bookings.router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


