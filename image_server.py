import asyncio
import json
import os
from pathlib import Path

from src.transporte.reliable import start_server, read_message, send_message
from src.transporte.fragmentation import unpack_chunk, Reassembler

SAVE_DIR = Path("received")
SAVE_DIR.mkdir(exist_ok=True)


async def on_message(data: bytes, writer, transport):
    """Handler que soporta recepción de imágenes fragmentadas y archivos simples."""
    # Intentar JSON primero
    try:
        pkt = json.loads(data.decode("utf-8"))
        ptype = pkt.get("type")

        # Mensaje de control
        if ptype == "control":
            print(f"[IMG SERVER] Control: {pkt.get('msg')}")
            return

        # Metadatos de imagen: iniciar recepción de chunks
        if ptype == "img_meta":
            name = pkt.get("name", "imagen_recibida.bin")
            size = int(pkt.get("size", 0))
            total_chunks = int(pkt.get("total_chunks", 0))
            print(f"[IMG SERVER] Preparando recepción de {name} ({size} bytes, {total_chunks} chunks)")

            # Crear reensamblador con timeout proporcional
            timeout = max(10.0, total_chunks * 0.2)
            reassembler = Reassembler(size, total_chunks, timeout=timeout)

            # Obtener reader desde writer (patrón usado en este proyecto)
            reader = writer._transport._protocol._stream_reader

            last_progress = 0
            while True:
                try:
                    pkt_bytes = await read_message(reader)
                except Exception:
                    # Conexión cerrada o lectura incompleta
                    break

                # Intentar desempaquetar chunk
                try:
                    meta_c, payload = unpack_chunk(pkt_bytes)
                except ValueError as e:
                    print(f"[IMG SERVER] Chunk inválido: {e}")
                    continue

                # Agregar chunk
                reassembler.add_chunk(meta_c["chunk_id"], meta_c["offset"], payload, meta_c.get("metadata"))

                # Enviar ACK de chunk (siempre, clientes FIABLE lo esperan; SEMI-FIABLE lo ignora)
                ack = json.dumps({"type": "ack", "chunk_id": meta_c["chunk_id"]}).encode()
                await send_message(writer, ack)

                # Progreso
                progress = reassembler.get_progress()
                if progress - last_progress >= 10:
                    print(f"[IMG SERVER] Progreso: {progress:.1f}%")
                    last_progress = progress

                if reassembler.is_complete():
                    break

            # Ensamblar y guardar
            assembled = reassembler.assemble()
            out_path = SAVE_DIR / name
            if assembled is None:
                partial = reassembler.assemble_partial()
                (SAVE_DIR / f"{name}.partial").write_bytes(partial)
                print(f"[IMG SERVER] Imagen parcial guardada: {out_path}.partial")
            else:
                out_path.write_bytes(assembled)
                print(f"[IMG SERVER] Imagen guardada: {out_path}")

            return

        # Archivo normal (no fragmentado)
        if ptype == "file":
            filename = pkt.get("name", "archivo_recibido.bin")
            size = int(pkt.get("size", 0))
            # Leer siguiente mensaje con datos
            reader = writer._transport._protocol._stream_reader
            filedata = await read_message(reader)
            (SAVE_DIR / filename).write_bytes(filedata)
            print(f"[IMG SERVER] Archivo guardado: {SAVE_DIR/filename} ({size} bytes)")
            return

        # Otros tipos JSON
        print(f"[IMG SERVER] Mensaje JSON no reconocido: {pkt}")
        return

    except (json.JSONDecodeError, UnicodeDecodeError):
        # Datos binarios inesperados; ignorar o registrar
        print(f"[IMG SERVER] Datos binarios recibidos ({len(data)} bytes) sin contexto de meta")
        return


async def main():
    host = "127.0.0.1"
    port = 9001
    print(f"[IMG SERVER] Iniciando en {host}:{port}...")
    await start_server(host, port, on_message)


if __name__ == "__main__":
    asyncio.run(main())
