from fastapi import FastAPI, UploadFile, File, HTTPException
import asyncio
import os
import sys
from pathlib import Path

# Ajustar sys.path para importar src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.app.cliente import send_file

app = FastAPI()

# Registros en memoria: username -> websocket, y mensajes no entregados
connections = {}
undelivered = {}

from fastapi import WebSocket, WebSocketDisconnect
import json

@app.post('/send')
async def send(file: UploadFile = File(...), host: str = '127.0.0.1', port: int = 9000):
    # Guardar temporalmente el archivo
    tmp_dir = Path(project_root) / 'frontend_api_tmp'
    tmp_dir.mkdir(exist_ok=True)
    tmp_path = tmp_dir / file.filename
    try:
        contents = await file.read()
        tmp_path.write_bytes(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")

    # Usar send_file del proyecto
    try:
        await send_file(host, port, str(tmp_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending file: {e}")

    # Opcional: borrar el archivo temporal
    try:
        tmp_path.unlink()
    except Exception:
        pass

    return {"status": "sent", "filename": file.filename}


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    username = None
    try:
    # El primer mensaje debe ser el JSON de registro: {"type":"register","username":"alice"}
        data = await websocket.receive_text()
        try:
            packet = json.loads(data)
        except Exception:
            await websocket.close(code=1003)
            return

        if packet.get('type') != 'register' or 'username' not in packet:
            await websocket.close(code=1008)
            return

        username = packet['username']
    # registrar
        connections[username] = websocket

    # entregar mensajes pendientes
        pending = undelivered.pop(username, [])
        for msg in pending:
            await websocket.send_text(json.dumps(msg))

    # bucle principal
        while True:
            text = await websocket.receive_text()
            try:
                pkt = json.loads(text)
            except Exception:
                # ignorar mensajes malformados
                continue

            if pkt.get('type') == 'message':
                to = pkt.get('to')
                out = {
                    'type': 'message',
                    'from': username,
                    'msg': pkt.get('msg', ''),
                }
                ws_to = connections.get(to)
                if ws_to:
                    try:
                        await ws_to.send_text(json.dumps(out))
                    except Exception:
                        # almacenar si falla el envío
                        undelivered.setdefault(to, []).append(out)
                else:
                    undelivered.setdefault(to, []).append(out)

            elif pkt.get('type') == 'list':
                # devolver lista de usuarios activos
                users = list(connections.keys())
                await websocket.send_text(json.dumps({'type': 'list', 'users': users}))

    except WebSocketDisconnect:
        pass
    finally:
        if username and connections.get(username) is websocket:
            del connections[username]
