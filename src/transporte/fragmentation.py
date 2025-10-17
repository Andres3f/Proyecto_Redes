import struct
import time
import gzip
import hashlib
import json
from typing import Optional, Dict, Tuple, List

# Formato de encabezado de chunk mejorado:
# 4s 1B  I     I      H        H         B      16s     H
# magic (4) | ver (1) | total_len (4) | offset (4) | chunk_id (2) | total_chunks (2) | flags (1) | hash (16) | meta_len (2)
# Seguido por metadatos JSON de longitud meta_len
HEADER_FMT = "!4sBIIHHB16sH"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
MAGIC = b'IMGC'
VERSION = 2

FLAG_COMPRESSED = 0x1
FLAG_HAS_METADATA = 0x2


def pack_chunk(data: bytes, total_len: int, offset: int, chunk_id: int, total_chunks: int, 
               compressed: bool = False, metadata: Optional[Dict] = None) -> bytes:
    """
    Empaqueta un chunk con metadatos mejorados para transferencia robusta de imágenes
    """
    flags = 0
    payload = data
    
    # Comprimir si se solicita
    if compressed:
        flags |= FLAG_COMPRESSED
        payload = gzip.compress(data)
    
    # Calcular hash MD5 del payload para verificación de integridad
    payload_hash = hashlib.md5(payload).digest()
    
    # Preparar metadatos
    meta_bytes = b''
    if metadata:
        flags |= FLAG_HAS_METADATA
        meta_bytes = json.dumps(metadata, separators=(',', ':')).encode('utf-8')
    
    meta_len = len(meta_bytes)
    if meta_len > 65535:  # Límite de 2 bytes para meta_len
        raise ValueError("Metadatos demasiado largos")
    
    header = struct.pack(HEADER_FMT, MAGIC, VERSION, total_len, offset, chunk_id, 
                        total_chunks, flags, payload_hash, meta_len)
    
    return header + meta_bytes + payload


def unpack_chunk(packet: bytes) -> Tuple[Dict, bytes]:
    """
    Desempaqueta un chunk con verificación de integridad y metadatos
    """
    if len(packet) < HEADER_SIZE:
        raise ValueError("Packet too small")
    
    header = packet[:HEADER_SIZE]
    magic, ver, total_len, offset, chunk_id, total_chunks, flags, payload_hash, meta_len = struct.unpack(HEADER_FMT, header)
    
    if magic != MAGIC:
        raise ValueError("Invalid magic")
    
    if ver != VERSION:
        # Para compatibilidad hacia atrás, permitir versión 1
        if ver == 1:
            # Usar formato anterior para versión 1
            return _unpack_chunk_v1(packet)
        else:
            raise ValueError(f"Unsupported version: {ver}")
    
    # Extraer metadatos
    metadata = None
    data_start = HEADER_SIZE
    if flags & FLAG_HAS_METADATA:
        if len(packet) < HEADER_SIZE + meta_len:
            raise ValueError("Packet too small for metadata")
        meta_bytes = packet[HEADER_SIZE:HEADER_SIZE + meta_len]
        try:
            metadata = json.loads(meta_bytes.decode('utf-8'))
        except Exception as e:
            raise ValueError(f"Invalid metadata: {e}")
        data_start = HEADER_SIZE + meta_len
    
    # Extraer payload
    payload = packet[data_start:]
    
    # Verificar hash de integridad
    calculated_hash = hashlib.md5(payload).digest()
    if calculated_hash != payload_hash:
        raise ValueError("Payload integrity check failed")
    
    # Descomprimir si es necesario
    compressed = bool(flags & FLAG_COMPRESSED)
    if compressed:
        try:
            payload = gzip.decompress(payload)
        except Exception as e:
            raise ValueError(f"Decompression failed: {e}")
    
    meta = {
        "version": ver,
        "total_len": total_len,
        "offset": offset,
        "chunk_id": chunk_id,
        "total_chunks": total_chunks,
        "flags": flags,
        "metadata": metadata,
        "integrity_verified": True
    }
    
    return meta, payload

def _unpack_chunk_v1(packet: bytes) -> Tuple[Dict, bytes]:
    """Compatibilidad con versión anterior"""
    OLD_HEADER_FMT = "!4sBIIHHB"
    OLD_HEADER_SIZE = struct.calcsize(OLD_HEADER_FMT)
    
    header = packet[:OLD_HEADER_SIZE]
    magic, ver, total_len, offset, chunk_id, total_chunks, flags = struct.unpack(OLD_HEADER_FMT, header)
    payload = packet[OLD_HEADER_SIZE:]
    
    compressed = bool(flags & FLAG_COMPRESSED)
    if compressed:
        try:
            payload = gzip.decompress(payload)
        except Exception:
            pass
    
    meta = {
        "version": ver,
        "total_len": total_len,
        "offset": offset,
        "chunk_id": chunk_id,
        "total_chunks": total_chunks,
        "flags": flags,
        "metadata": None,
        "integrity_verified": False
    }
    return meta, payload


class Reassembler:
    def __init__(self, total_len: int, total_chunks: int, timeout: float = 10.0):
        self.total_len = total_len
        self.total_chunks = total_chunks
        self.received: Dict[int, bytes] = {}
        self.metadata: Dict[int, Dict] = {}  # Metadatos por chunk
        self.missing_chunks: set = set(range(total_chunks))
        self.start_time = time.time()
        self.timeout = timeout

    def add_chunk(self, chunk_id: int, offset: int, data: bytes, metadata: Optional[Dict] = None) -> bool:
        """
        Añade un chunk al reensamblador.
        Retorna True si es un chunk nuevo, False si ya existía.
        """
        if chunk_id in self.received:
            return False
        
        if chunk_id < 0 or chunk_id >= self.total_chunks:
            raise ValueError(f"Invalid chunk_id: {chunk_id}")
        
        self.received[chunk_id] = data
        if metadata:
            self.metadata[chunk_id] = metadata
        
        self.missing_chunks.discard(chunk_id)
        return True

    def get_missing_chunks(self) -> List[int]:
        """Retorna la lista de chunks faltantes"""
        return sorted(list(self.missing_chunks))

    def is_complete(self) -> bool:
        return len(self.missing_chunks) == 0

    def get_progress(self) -> float:
        """Retorna el progreso como porcentaje (0-100)"""
        return (len(self.received) / self.total_chunks) * 100

    def assemble(self) -> Optional[bytes]:
        """
        Ensambla los chunks recibidos.
        Retorna None si faltan chunks críticos.
        """
        if not self.received:
            return None
        
        # Ensamblar basado en orden de chunk_id
        out = bytearray()
        total_assembled = 0
        
        for i in range(self.total_chunks):
            part = self.received.get(i)
            if part is None:
                # Chunk faltante - no se puede ensamblar completamente
                return None
            out.extend(part)
            total_assembled += len(part)
        
        # Recortar al tamaño total esperado
        result = bytes(out)[:self.total_len]
        
        # Verificación adicional de tamaño
        if len(result) != self.total_len:
            return None
            
        return result

    def assemble_partial(self) -> bytes:
        """
        Ensambla chunks parciales, rellenando huecos con zeros.
        Útil para visualizar archivos parcialmente recibidos.
        """
        if not self.received:
            return b''
        
        # Calcular tamaño promedio de chunk
        if self.received:
            avg_chunk_size = sum(len(data) for data in self.received.values()) // len(self.received)
        else:
            avg_chunk_size = self.total_len // self.total_chunks
        
        out = bytearray()
        for i in range(self.total_chunks):
            part = self.received.get(i)
            if part is None:
                # Rellenar con zeros
                expected_size = min(avg_chunk_size, self.total_len - len(out))
                out.extend(b'\x00' * expected_size)
            else:
                out.extend(part)
        
        return bytes(out)[:self.total_len]

    def is_timed_out(self) -> bool:
        return (time.time() - self.start_time) > self.timeout

    def get_status(self) -> Dict:
        """Retorna estado detallado del reensamblador"""
        return {
            "total_chunks": self.total_chunks,
            "received_chunks": len(self.received),
            "missing_chunks": self.get_missing_chunks(),
            "progress": self.get_progress(),
            "is_complete": self.is_complete(),
            "is_timed_out": self.is_timed_out(),
            "elapsed_time": time.time() - self.start_time
        }
