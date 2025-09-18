from fastapi import FastAPI
from src.routes import call
from src.websocket import ws

app = FastAPI()

# Include HTTP routes
app.include_router(call.router, prefix="/call")

# Include WebSocket routes
app.include_router(ws.router, prefix="/ws")

@app.get("/")
def health():
    return {"status": "ok"}
