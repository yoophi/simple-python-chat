import asyncio

import aioredis
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from loguru import logger

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await redis_connector(websocket)


async def redis_connector(
        websocket: WebSocket, redis_uri: str = "redis://localhost:6379"
):
    async def consumer_handler(ws: WebSocket, r):
        try:
            while True:
                message = await ws.receive_text()
                if message:
                    await r.publish("chat:c", message)
        except WebSocketDisconnect as exc:
            # TODO this needs handling better
            logger.error(exc)

    async def producer_handler(r, ws: WebSocket):
        (channel,) = await r.subscribe("chat:c")
        assert isinstance(channel, aioredis.Channel)
        try:
            while True:
                message = await channel.get()
                if message:
                    await ws.send_text(message.decode("utf-8"))
        except Exception as exc:
            # TODO this needs handling better
            logger.error(exc)

    redis = await aioredis.create_redis_pool(redis_uri)

    consumer_task = consumer_handler(websocket, redis)
    producer_task = producer_handler(redis, websocket)
    done, pending = await asyncio.wait(
        [consumer_task, producer_task], return_when=asyncio.FIRST_COMPLETED,
    )
    logger.debug(f"Done task: {done}")
    for task in pending:
        logger.debug(f"Canceling task: {task}")
        task.cancel()
    redis.close()
    await redis.wait_closed()
