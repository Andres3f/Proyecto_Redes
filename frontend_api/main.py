
from fastapi import Request
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
import asyncio
import os
import sys
from pathlib import Path

# Ajustar sys.path para importar src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.app.cliente import send_file, send_image_fragmented_fiable


from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite conexiones desde cualquier origen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Servir archivos recibidos (imágenes) en /received/
import os
received_dir = os.path.abspath(os.path.join(project_root, 'received'))
if not os.path.exists(received_dir):
    os.makedirs(received_dir)
app.mount('/received', StaticFiles(directory=received_dir), name='received')

# Registros en memoria: username -> websocket, mensajes no entregados y mapeo de IPs
connections = {}
undelivered = {}
user_ips = {}  # Diccionario global para mantener las IPs de los usuarios

from fastapi import WebSocket, WebSocketDisconnect
import json

from fastapi import Form
from typing import Optional
import uuid

@app.post('/send')
async def send(
    file: UploadFile = File(...), 
    host: str = '127.0.0.1',
    port: int = 9001,
    mode: str = Form('FIABLE'),
    loss_rate: float = Form(0.1),
    chunk_size: int = Form(1024),
    enable_compression: bool = Form(True)
):
    return await _handle_upload(file, host, port, mode, loss_rate, chunk_size, enable_compression)

# Nuevo endpoint para compatibilidad con el frontend
@app.post('/upload-image')
async def upload_image(
    file: UploadFile = File(...),
    transfer_mode: str = Form('FIABLE'),
    chunk_size: int = Form(1024),
    max_retries: int = Form(3),
    host: str = '127.0.0.1',
    port: int = 9000,
    loss_rate: float = Form(0.1),
    enable_compression: bool = Form(True)
):
    # Mapear los nombres de los campos del frontend a los del backend
    mode = transfer_mode
    return await _handle_upload(file, host, port, mode, loss_rate, chunk_size, enable_compression)

# Lógica compartida para ambos endpoints
async def _handle_upload(file, host, port, mode, loss_rate, chunk_size, enable_compression):
    """
    Endpoint mejorado para envío de archivos con fragmentación configurable
    """
    # Validar parámetros
    if mode not in ['FIABLE', 'SEMI-FIABLE']:
        raise HTTPException(status_code=400, detail="Modo debe ser 'FIABLE' o 'SEMI-FIABLE'")
    
    if not (0.0 <= loss_rate <= 1.0):
        raise HTTPException(status_code=400, detail="loss_rate debe estar entre 0.0 y 1.0")
    
    if chunk_size < 64 or chunk_size > 65536:
        raise HTTPException(status_code=400, detail="chunk_size debe estar entre 64 y 65536")
    
    # Guardar temporalmente el archivo
    tmp_dir = Path(project_root) / 'frontend_api_tmp'
    tmp_dir.mkdir(exist_ok=True)
    tmp_path = tmp_dir / file.filename
    

    try:
        contents = await file.read()
        tmp_path.write_bytes(contents)
        file_size = len(contents)
        print(f"[API] Procesando {file.filename} ({file_size} bytes)")
        print(f"      Modo: {mode}, Loss rate: {loss_rate}, Chunk size: {chunk_size}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")

    # Detectar tipo de archivo
    import mimetypes
    mime, _ = mimetypes.guess_type(str(tmp_path))
    
    # Inicializar variables
    safe_name = file.filename
    modo = mode
    
    try:
        import shutil
        import uuid
        if mime and mime.startswith('image/'):
            # Guardar imagen directamente en received para visualización inmediata
            received_dir = os.path.abspath(os.path.join(project_root, 'received'))
            if not os.path.exists(received_dir):
                os.makedirs(received_dir)
            ext = os.path.splitext(file.filename)[1] or '.png'
            safe_name = f"img_{uuid.uuid4().hex}{ext}"
            dest_path = os.path.join(received_dir, safe_name)
            shutil.copy(str(tmp_path), dest_path)
            print(f"[API] ✅ Imagen guardada localmente: {dest_path}")
            modo = f'{mode}-IMG-LOCAL'
            
            # Ahora intentar enviar al servidor de transporte (opcional, no bloqueante para el usuario)
            try:
                if mode == 'FIABLE':
                    from src.app.cliente import send_image_fragmented_fiable
                    await send_image_fragmented_fiable(host, port, str(tmp_path), chunk_size=chunk_size, max_retries=5, ack_timeout=0.5)
                    modo = f'{mode}-IMG-FRAGMENTED-ENVIADO'
                    print(f"[API] ✅ Imagen también enviada al servidor de transporte en {host}:{port}")
                elif mode == 'SEMI-FIABLE':
                    from src.app.cliente import send_image_fragmented_semi_fiable
                    await send_image_fragmented_semi_fiable(host, port, str(tmp_path), chunk_size=chunk_size, enable_compression=enable_compression)
                    modo = f'{mode}-IMG-FRAGMENTED-ENVIADO'
                    print(f"[API] ✅ Imagen también enviada al servidor de transporte en {host}:{port}")
            except Exception as e:
                # Si falla el envío al servidor, la imagen ya está guardada localmente
                print(f"[API] ⚠️ No se pudo enviar al servidor de transporte: {e} (pero la imagen está disponible localmente)")
        else:
            # Archivo normal
            await send_file(host, port, str(tmp_path))
            modo = f'{mode}-NORMAL'
    except Exception as e:
        print(f"[API] ❌ Error al procesar archivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {e}")

    # Limpiar archivo temporal
    try:
        tmp_path.unlink()
    except Exception:
        pass

    return {
        "status": "sent", 
        "filename": safe_name if mime and mime.startswith('image/') else file.filename, 
        "mode": modo,
        "size": file_size,
        "chunks": (file_size + chunk_size - 1) // chunk_size,
        "config": {
            "mode": mode,
            "loss_rate": loss_rate,
            "chunk_size": chunk_size,
            "compression": enable_compression
        }
    }

async def send_image_with_config(host: str, port: int, filepath: str, mode: str, 
                               loss_rate: float, chunk_size: int, enable_compression: bool) -> bool:
    """
    Envía imagen con configuración específica usando el demo mejorado
    """
    try:
        # Importar y usar el cliente del demo
        from examples.pruebdemo_img_transfer import client_send_image
        
        client_stats = await client_send_image(
            host, port, filepath, mode, loss_rate, 
            chunk_size=chunk_size, enable_compression=enable_compression
        )
        
        print(f"[API] Transferencia completada: {client_stats}")
        return True
        
    except Exception as e:
        print(f"[API] Error en transferencia: {e}")
        return False


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    username = None
    
    try:
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
    # registrar conexión y actualizar IP
        connections[username] = websocket
        
        # Obtener y guardar IP del usuario
        headers = websocket.headers
        client_ip = (
            headers.get('x-real-ip') or 
            headers.get('x-forwarded-for', '').split(',')[0].strip() or 
            websocket.client.host or 
            '127.0.0.1'
        )
        
        # Guardar IP del usuario
        user_ips[username] = client_ip
        print(f"[WebSocket] Usuario {username} registrado con IP: {client_ip}")
        
        # Notificar IP asignada al usuario
        await websocket.send_text(json.dumps({
            'type': 'ip_assigned',
            'ip': client_ip,
            'username': username
        }))
        
        # Notificar a todos los usuarios conectados la actualización de IPs
        for ws in connections.values():
            try:
                await ws.send_text(json.dumps({
                    'type': 'user_list_update',
                    'users': list(connections.keys()),
                    'userIPs': user_ips
                }))
            except Exception as e:
                print(f"[WebSocket] Error al actualizar lista de usuarios: {e}")

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
                # Crear información de simulación de capas
                session_id = str(uuid.uuid4())[:8]
                sequence_number = len(undelivered.get(to, [])) + 1
                source_ip = user_ips.get(username, client_ip)
                dest_ip = user_ips.get(to, "unknown")
                
                print(f"[WebSocket] Enviando mensaje de {username}({source_ip}) a {to}({dest_ip})")
                
                # Mensaje con información de capas para simulación
                out = {
                    'type': 'message',
                    'from': username,
                    'to': to,  # Añadir el destinatario explícitamente
                    'msg': pkt.get('msg', ''),
                    'layerInfo': {
                        'sessionId': session_id,
                        'sequence': sequence_number,
                        'reliable': True,
                        'fragmentId': f"MSG-{sequence_number}",
                        'sourceIp': source_ip,
                        'destIp': dest_ip,
                        'sourceUser': username,
                        'destUser': to
                    }
                }
                print(f"[WebSocket] Enviando mensaje con capas: {out['layerInfo']}")
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
                # devolver lista de usuarios activos y sus IPs
                users = list(connections.keys())
                print(f"[WebSocket] Enviando lista de usuarios a {username}. IPs actuales: {user_ips}")
                await websocket.send_text(json.dumps({
                    'type': 'list',
                    'users': users,
                    'userIPs': user_ips,
                    'currentUser': username
                }))

    except WebSocketDisconnect:
        if username and connections.get(username) is websocket:
            del connections[username]
            if username in user_ips:
                del user_ips[username]
    finally:
        if username and connections.get(username) is websocket:
            del connections[username]
            if username in user_ips:
                del user_ips[username]
