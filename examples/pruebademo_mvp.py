import asyncio
import json
from pathlib import Path
from src.transporte.reliable import start_server

SAVE_DIR = Path("received")
SAVE_DIR.mkdir(exist_ok=True)

async def on_message(data: bytes, writer):
    from src.transporte.reliable import read_message
    try:
        packet = json.loads(data.decode())
        if packet.get("type") == "control":
            print("[Servidor] Control:", packet["msg"])
        elif packet.get("type") == "file":
            meta = packet
            # Esperar el siguiente mensaje: los datos reales del archivo
            filedata = await read_message(writer._transport._protocol._stream_reader)
            filename = meta.get("name", "archivo_recibido.bin")
            (SAVE_DIR / filename).write_bytes(filedata)
            print(f"[Servidor] Archivo guardado en {SAVE_DIR/filename}")
        else:
            print("[Servidor] Mensaje desconocido:", packet)
    except json.JSONDecodeError:
        # Datos binarios del archivo (fallback)
        filename = "archivo_recibido.bin"
        (SAVE_DIR / filename).write_bytes(data)
        print(f"[Servidor] Archivo guardado en {SAVE_DIR/filename}")

async def main():
    await start_server("0.0.0.0", 9000, on_message)

if __name__ == "__main__":
    asyncio.run(main())
