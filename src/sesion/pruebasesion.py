import json
import uuid
from src.transporte.reliable import send_message

class Session:
    def __init__(self, writer):
        self.id = str(uuid.uuid4())
        self.writer = writer

    async def send_control(self, msg_type: str, payload: dict):
        packet = {
            "session_id": self.id,
            "type": msg_type,
            "payload": payload
        }
        data = json.dumps(packet).encode('utf-8')
        await send_message(self.writer, data)
