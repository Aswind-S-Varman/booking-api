from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from . import web
from .routers import auth, bookings, resources

app = FastAPI(
    title="Booking API",
    description="Book shared resources without double-booking them.",
    version="0.1.0",
)

app.include_router(auth.router)
app.include_router(resources.router)
app.include_router(bookings.router)
app.include_router(web.router)


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse("/ui/resources")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


