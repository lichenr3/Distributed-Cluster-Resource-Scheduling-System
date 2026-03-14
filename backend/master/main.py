from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket

from master.core.events import lifespan
from master.routers import internal, tasks, workers
from master.ws.cluster import cluster_ws_endpoint
from master.ws.logs import logs_ws_endpoint

app = FastAPI(title="Mini Scheduler Master", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(workers.router)
app.include_router(internal.router)


@app.websocket("/ws/cluster")
async def cluster_websocket_endpoint(websocket: WebSocket):
    await cluster_ws_endpoint(websocket)


@app.websocket("/ws/logs/{task_id}")
async def logs_websocket_endpoint(websocket: WebSocket, task_id: str):
    await logs_ws_endpoint(websocket, task_id)
