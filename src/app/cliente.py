import asyncio
import json
import os
from src.transporte.reliable import send_message, read_message

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
