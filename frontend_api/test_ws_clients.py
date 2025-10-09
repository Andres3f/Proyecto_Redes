import asyncio
import websockets
import json

async def client(register_name, to, msg):
    uri = 'ws://127.0.0.1:8000/ws'
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({'type':'register','username': register_name}))
        # esperar un momento y luego enviar el mensaje
        await asyncio.sleep(0.5)
        await ws.send(json.dumps({'type':'message','to': to, 'msg': msg}))
        # esperar para recibir mensajes
        try:
            for _ in range(2):
                data = await asyncio.wait_for(ws.recv(), timeout=2)
                print(f"{register_name} received: {data}")
        except asyncio.TimeoutError:
            pass

async def main():
    # Ejecutar dos clientes concurrentes: alice envía a bob
    await asyncio.gather(
        client('alice', 'bob', 'Hola Bob! soy Alice'),
        client('bob', 'alice', 'Hola Alice! soy Bob')
    )

if __name__ == '__main__':
    asyncio.run(main())
