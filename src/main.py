from fastapi import FastAPI
from src.routes import call
from src.websocket import ws
from src.middleware.validator import RequestValidatorMiddleware

app = FastAPI()

# Include HTTP routes
app.include_router(call.router, prefix="/call")

# Include WebSocket routes
app.include_router(ws.router, prefix="/ws")

# Add request validator for HTTP routes as middleware
app.add_middleware(RequestValidatorMiddleware)


@app.get("/")
def health():
    return {"status": "ok"}
