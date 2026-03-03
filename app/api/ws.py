from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from app.infrastructure.ws_manager import ws_manager

router = APIRouter()

_TEST_PAGE = """\
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>WebSocket Test</title>
    <style>
        body { font-family: monospace; max-width: 640px; margin: 2rem auto; }
        #log { background: #111; color: #0f0; padding: 1rem; height: 300px;
               overflow-y: auto; white-space: pre-wrap; border-radius: 4px; }
        button { margin: 0.5rem 0.25rem; padding: 0.4rem 1rem; cursor: pointer; }
    </style>
</head>
<body>
    <h2>WebSocket — File Events</h2>
    <button onclick="connect()">Connect</button>
    <button onclick="disconnect()">Disconnect</button>
    <div id="log"></div>
    <script>
        let ws = null;
        const log = document.getElementById("log");
        function addLog(msg) { log.textContent += msg + "\\n"; log.scrollTop = log.scrollHeight; }

        function connect() {
            if (ws) { addLog("Already connected."); return; }
            const proto = location.protocol === "https:" ? "wss:" : "ws:";
            ws = new WebSocket(proto + "//" + location.host + "/ws/files");
            ws.onopen = () => addLog("[connected]");
            ws.onmessage = (e) => addLog("[event] " + e.data);
            ws.onclose = () => { addLog("[disconnected]"); ws = null; };
            ws.onerror = () => addLog("[error]");
        }

        function disconnect() {
            if (ws) ws.close();
        }
    </script>
</body>
</html>
"""


@router.get("/ws-test", response_class=HTMLResponse, include_in_schema=False)
async def ws_test_page():
    """Тестовая страница для WebSocket."""
    return _TEST_PAGE


@router.websocket("/ws/files")
async def ws_files(ws: WebSocket):
    """WebSocket для получения событий об изменении файлов."""
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(ws)
