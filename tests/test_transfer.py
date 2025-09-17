import asyncio
import tempfile
import os
import pytest
from src.transporte import reliable

@pytest.mark.asyncio
async def test_send_and_receive():
    messages = []
    async def on_msg(data, w):
        messages.append(data)

    server = await asyncio.start_server(lambda r, w: reliable.handle_client(r, w, on_msg),
                                        "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()

    async def client():
        reader, writer = await asyncio.open_connection(host, port)
        await reliable.send_message(writer, b"hola")
        writer.close()
        await writer.wait_closed()

    await asyncio.gather(client())
    server.close()
    await server.wait_closed()
    assert messages[0] == b"hola"
