import asyncio
import struct

HEADER_FMT = "!I"  # 4 bytes para longitud del mensaje

async def send_message(writer: asyncio.StreamWriter, data: bytes):
    header = struct.pack(HEADER_FMT, len(data))
    writer.write(header + data)
    await writer.drain()

async def read_message(reader: asyncio.StreamReader) -> bytes:
    header = await reader.readexactly(4)
    (length,) = struct.unpack(HEADER_FMT, header)
    return await reader.readexactly(length)

async def start_server(host: str, port: int, on_message):
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, on_message),
        host, port)
    async with server:
        await server.serve_forever()

async def handle_client(reader, writer, on_message):
    peer = writer.get_extra_info('peername')
    print(f"[Transporte] Conexión desde {peer}")
    try:
        while True:
            data = await read_message(reader)
            await on_message(data, writer)
    except asyncio.IncompleteReadError:
        print(f"[Transporte] Cliente {peer} desconectado.")
    finally:
        writer.close()
        await writer.wait_closed()
