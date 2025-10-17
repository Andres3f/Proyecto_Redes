import asyncio
import struct
import time
import json
import random
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass

HEADER_FMT = "!I"  # 4 bytes para longitud del mensaje

# Configuración de transporte confiable
@dataclass
class ReliableConfig:
    ack_timeout: float = 1.0      # Timeout para ACKs
    max_retries: int = 5          # Máximo número de reintentos
    window_size: int = 10         # Tamaño de ventana deslizante
    loss_simulation: float = 0.0  # Tasa de pérdida simulada (0.0-1.0)

class ReliableTransport:
    def __init__(self, config: ReliableConfig = None):
        self.config = config or ReliableConfig()
        self.seq_num = 0
        self.pending_acks: Dict[int, asyncio.Event] = {}
        self.received_packets: Dict[int, bytes] = {}
        
    async def send_reliable(self, writer: asyncio.StreamWriter, data: bytes, 
                           packet_type: str = "data") -> bool:
        """
        Envía datos de forma confiable con ACK y reintentos
        """
        seq = self.seq_num
        self.seq_num += 1
        
        packet = {
            "type": packet_type,
            "seq": seq,
            "data": data.hex() if isinstance(data, bytes) else data,
            "timestamp": time.time()
        }
        
        packet_bytes = json.dumps(packet).encode('utf-8')
        
        # Crear evento para esperar ACK
        ack_event = asyncio.Event()
        self.pending_acks[seq] = ack_event
        
        try:
            for attempt in range(self.config.max_retries):
                # Simular pérdida de paquetes
                if random.random() < self.config.loss_simulation:
                    print(f"[RELIABLE] Simulando pérdida de paquete seq={seq}, intento {attempt + 1}")
                    continue
                
                # Enviar paquete
                await send_message(writer, packet_bytes)
                print(f"[RELIABLE] Enviado paquete seq={seq}, intento {attempt + 1}")
                
                # Esperar ACK con timeout
                try:
                    await asyncio.wait_for(ack_event.wait(), timeout=self.config.ack_timeout)
                    print(f"[RELIABLE] ACK recibido para seq={seq}")
                    return True
                except asyncio.TimeoutError:
                    print(f"[RELIABLE] Timeout esperando ACK para seq={seq}, intento {attempt + 1}")
                    ack_event.clear()
            
            print(f"[RELIABLE] Falló envío después de {self.config.max_retries} intentos, seq={seq}")
            return False
            
        finally:
            # Limpiar
            self.pending_acks.pop(seq, None)
    
    def handle_ack(self, seq: int):
        """Maneja ACK recibido"""
        if seq in self.pending_acks:
            self.pending_acks[seq].set()
    
    async def send_ack(self, writer: asyncio.StreamWriter, seq: int):
        """Envía ACK para un paquete recibido"""
        ack_packet = {
            "type": "ack",
            "seq": seq,
            "timestamp": time.time()
        }
        await send_message(writer, json.dumps(ack_packet).encode('utf-8'))
        print(f"[RELIABLE] ACK enviado para seq={seq}")

async def send_message(writer: asyncio.StreamWriter, data: bytes):
    """Envía mensaje con encabezado de longitud"""
    header = struct.pack(HEADER_FMT, len(data))
    writer.write(header + data)
    await writer.drain()

async def read_message(reader: asyncio.StreamReader) -> bytes:
    """Lee mensaje con encabezado de longitud"""
    header = await reader.readexactly(4)
    (length,) = struct.unpack(HEADER_FMT, header)
    return await reader.readexactly(length)

async def start_server(host: str, port: int, on_message: Callable):
    """Inicia servidor con manejo mejorado"""
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, on_message),
        host, port)
    async with server:
        await server.serve_forever()

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, 
                       on_message: Callable):
    """Maneja cliente con transporte confiable"""
    peer = writer.get_extra_info('peername')
    print(f"[Transporte] Conexión desde {peer}")
    
    transport = ReliableTransport()
    
    try:
        while True:
            raw_data = await read_message(reader)
            
            try:
                # Intentar parsear como JSON (para paquetes del protocolo confiable)
                packet = json.loads(raw_data.decode('utf-8'))
                
                if packet.get("type") == "ack":
                    # Manejar ACK
                    transport.handle_ack(packet["seq"])
                    continue
                elif packet.get("type") == "data":
                    # Paquete de datos - enviar ACK y procesar
                    seq = packet["seq"]
                    await transport.send_ack(writer, seq)
                    
                    # Convertir datos de hex a bytes si es necesario
                    data = packet.get("data", "")
                    if isinstance(data, str):
                        try:
                            data = bytes.fromhex(data)
                        except ValueError:
                            data = data.encode('utf-8')
                    
                    await on_message(data, writer, transport)
                else:
                    # Otro tipo de paquete
                    await on_message(raw_data, writer, transport)
                    
            except (json.JSONDecodeError, UnicodeDecodeError):
                # No es JSON válido, tratar como datos raw
                await on_message(raw_data, writer, transport)
                
    except asyncio.IncompleteReadError:
        print(f"[Transporte] Cliente {peer} desconectado.")
    except Exception as e:
        print(f"[Transporte] Error con cliente {peer}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

# Funciones de utilidad para testing
async def send_file_reliable(host: str, port: int, filepath: str, 
                           config: ReliableConfig = None) -> bool:
    """Envía archivo usando transporte confiable"""
    transport = ReliableTransport(config)
    
    try:
        reader, writer = await asyncio.open_connection(host, port)
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # Enviar metadatos del archivo
        import os
        metadata = {
            "filename": os.path.basename(filepath),
            "size": len(data),
            "type": "file"
        }
        
        success = await transport.send_reliable(writer, json.dumps(metadata).encode(), "metadata")
        if not success:
            return False
        
        # Enviar datos del archivo
        success = await transport.send_reliable(writer, data, "file_data")
        
        writer.close()
        await writer.wait_closed()
        
        return success
        
    except Exception as e:
        print(f"[RELIABLE] Error enviando archivo: {e}")
        return False
