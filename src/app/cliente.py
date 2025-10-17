async def send_image_fragmented_semi_fiable(host, port, filepath, chunk_size=1024, enable_compression=False):
    """Envía una imagen fragmentada en modo SEMI-FIABLE (sin ACKs ni reintentos)."""
    import mimetypes
    filename = os.path.basename(filepath)
    mime, _ = mimetypes.guess_type(filename)
    if not (mime and mime.startswith('image/')):
        raise ValueError("Solo se permite enviar imágenes con este método")

    reader, writer = await asyncio.open_connection(host, port)
    with open(filepath, 'rb') as f:
        data = f.read()
    total_len = len(data)
    total_chunks = (total_len + chunk_size - 1) // chunk_size

    # Enviar control
    ctrl = {"type": "control", "msg": f"send image {filename}"}
    await send_message(writer, json.dumps(ctrl).encode())

    # Enviar metadatos
    meta = {"type": "img_meta", "name": filename, "size": total_len, "total_chunks": total_chunks}
    await send_message(writer, json.dumps(meta).encode())

    # Enviar chunks sin ACK ni reintentos
    for i in range(total_chunks):
        offset = i * chunk_size
        part = data[offset:offset + chunk_size]
        pkt = pack_chunk(part, total_len, offset, i, total_chunks, compressed=enable_compression)
        await send_message(writer, pkt)

    writer.close()
    await writer.wait_closed()
import asyncio
import json
import os
import mimetypes
from src.transporte.reliable import send_message, read_message
from src.transporte.fragmentation import pack_chunk

async def send_image_fragmented_fiable(host, port, filepath, chunk_size=1024, max_retries=5, ack_timeout=0.5):
    """Envía una imagen fragmentada en modo FIABLE (con ACKs y reintentos por chunk)."""
    filename = os.path.basename(filepath)
    mime, _ = mimetypes.guess_type(filename)
    if not (mime and mime.startswith('image/')):
        raise ValueError("Solo se permite enviar imágenes con este método")
    
    try:
        reader, writer = await asyncio.open_connection(host, port)
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        total_len = len(data)
        total_chunks = (total_len + chunk_size - 1) // chunk_size
        
        print(f"[Cliente] Conectado a {host}:{port}, enviando {filename} ({total_chunks} chunks)")
        
        # Enviar control
        ctrl = {"type": "control", "msg": f"send image {filename}"}
        await send_message(writer, json.dumps(ctrl).encode())
        
        # Enviar metadatos
        meta = {"type": "img_meta", "name": filename, "size": total_len, "total_chunks": total_chunks}
        await send_message(writer, json.dumps(meta).encode())

        # Enviar chunks con ACK
        for i in range(total_chunks):
            offset = i * chunk_size
            part = data[offset:offset + chunk_size]
            pkt = pack_chunk(part, total_len, offset, i, total_chunks, compressed=False)
            
            retries = 0
            while retries < max_retries:
                await send_message(writer, pkt)
                try:
                    ack_raw = await asyncio.wait_for(read_message(reader), timeout=ack_timeout)
                    ack = json.loads(ack_raw)
                    if ack.get('type') == 'ack' and ack.get('chunk_id') == i:
                        break
                except asyncio.TimeoutError:
                    retries += 1
                    print(f"[Cliente] Timeout esperando ACK chunk {i}, reintento {retries}/{max_retries}")
                except Exception as e:
                    retries += 1
                    print(f"[Cliente] Error esperando ACK chunk {i}: {e}, reintento {retries}/{max_retries}")
            else:
                print(f"[Cliente] ⚠️ Chunk {i} no fue ACKeado tras {max_retries} intentos")
        
        print(f"[Cliente] ✅ Imagen {filename} enviada completamente")
        writer.close()
        await writer.wait_closed()
        
    except ConnectionRefusedError:
        raise Exception(f"No se pudo conectar al servidor en {host}:{port}. ¿Está corriendo el servidor de imágenes?")
    except Exception as e:
        print(f"[Cliente] Error enviando imagen: {e}")
        raise

async def send_file(host, port, filepath):
    reader, writer = await asyncio.open_connection(host, port)
    filename = os.path.basename(filepath)

    # 1. Enviar mensaje de control
    ctrl = {"type": "control", "msg": f"Inicio de envío: {filename}"}
    await send_message(writer, json.dumps(ctrl).encode())

    # 2. Enviar archivo en un solo bloque (avance 1 = simple)
    with open(filepath, "rb") as f:
        data = f.read()
    meta = {"type": "file", "name": filename, "size": len(data)}
    await send_message(writer, json.dumps(meta).encode())
    await send_message(writer, data)

    print(f"[App] Archivo {filename} enviado ({len(data)} bytes).")
    writer.close()
    await writer.wait_closed()
