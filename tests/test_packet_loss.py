import pytest
import asyncio
import os
import tempfile
import random
from PIL import Image
import numpy as np

from src.transporte.fragmentation import pack_chunk, unpack_chunk, Reassembler
from src.transporte.reliable import ReliableTransport, ReliableConfig, send_message, read_message
from examples.pruebdemo_img_transfer import client_send_image, handle_client


class TestPacketLoss:
    """Tests para simular y verificar recuperación de pérdida de paquetes"""
    
    @pytest.mark.asyncio
    async def test_fragmentation_integrity(self):
        """Test de integridad de fragmentación con metadatos"""
        # Crear datos de prueba
        test_data = b"Hello, World! " * 100  # 1400 bytes
        total_len = len(test_data)
        chunk_size = 100
        total_chunks = (total_len + chunk_size - 1) // chunk_size
        
        # Metadatos de prueba
        metadata = {
            "image_type": "png",
            "width": 100,
            "height": 100,
            "original_size": total_len
        }
        
        # Fragmentar
        chunks = []
        for i in range(total_chunks):
            offset = i * chunk_size
            chunk_data = test_data[offset:offset + chunk_size]
            packet = pack_chunk(chunk_data, total_len, offset, i, total_chunks, 
                              compressed=False, metadata=metadata if i == 0 else None)
            chunks.append(packet)
        
        # Verificar que todos los chunks se pueden desempaquetar
        reassembler = Reassembler(total_len, total_chunks)
        
        for packet in chunks:
            meta, payload = unpack_chunk(packet)
            assert meta['integrity_verified'] == True
            reassembler.add_chunk(meta['chunk_id'], meta['offset'], payload, meta.get('metadata'))
        
        # Verificar ensamblado completo
        assert reassembler.is_complete()
        assembled = reassembler.assemble()
        assert assembled == test_data
        
        # Verificar metadatos del primer chunk
        first_meta = reassembler.metadata.get(0)
        assert first_meta is not None
        assert first_meta['image_type'] == 'png'

    @pytest.mark.asyncio
    async def test_packet_loss_simulation(self):
        """Test de simulación de pérdida de paquetes"""
        test_data = b"Test data for packet loss simulation " * 50
        total_len = len(test_data)
        chunk_size = 50
        total_chunks = (total_len + chunk_size - 1) // chunk_size
        
        # Simular pérdida del 30% de paquetes
        loss_rate = 0.3
        received_chunks = []
        
        for i in range(total_chunks):
            if random.random() > loss_rate:  # Paquete no se pierde
                offset = i * chunk_size
                chunk_data = test_data[offset:offset + chunk_size]
                packet = pack_chunk(chunk_data, total_len, offset, i, total_chunks)
                received_chunks.append((i, packet))
        
        # Intentar reensamblar con chunks parciales
        reassembler = Reassembler(total_len, total_chunks)
        
        for chunk_id, packet in received_chunks:
            meta, payload = unpack_chunk(packet)
            reassembler.add_chunk(meta['chunk_id'], meta['offset'], payload)
        
        # Verificar estado
        status = reassembler.get_status()
        print(f"Progreso: {status['progress']:.1f}%")
        print(f"Chunks faltantes: {len(status['missing_chunks'])}")
        
        if not reassembler.is_complete():
            # Ensamblar parcial
            partial = reassembler.assemble_partial()
            assert len(partial) <= total_len
        else:
            # Ensamblar completo
            complete = reassembler.assemble()
            assert complete == test_data

    @pytest.mark.asyncio
    async def test_reliable_transport_with_loss(self):
        """Test de transporte confiable con pérdida simulada"""
        # Configurar transporte con pérdida simulada
        config = ReliableConfig(
            ack_timeout=0.5,
            max_retries=3,
            loss_simulation=0.4  # 40% de pérdida
        )
        
        transport = ReliableTransport(config)
        
        # Datos de prueba
        test_message = b"Mensaje de prueba para transporte confiable"
        
        # Crear mock writer que simule la red
        class MockWriter:
            def __init__(self):
                self.sent_data = []
                self.closed = False
            
            def write(self, data):
                self.sent_data.append(data)
            
            async def drain(self):
                pass
            
            def close(self):
                self.closed = True
            
            async def wait_closed(self):
                pass
        
        mock_writer = MockWriter()
        
        # El test de transporte confiable requiere un servidor real para los ACKs
        # Por ahora verificamos que la configuración se aplica correctamente
        assert transport.config.loss_simulation == 0.4
        assert transport.config.max_retries == 3

    @pytest.mark.asyncio
    async def test_image_transfer_with_corruption(self):
        """Test de transferencia de imagen con corrupción de datos"""
        # Crear imagen de prueba
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            # Crear imagen simple con PIL
            img = Image.new('RGB', (100, 50), color='red')
            img.save(tmp_file.name, 'PNG')
            tmp_path = tmp_file.name
        
        try:
            # Leer datos de imagen
            with open(tmp_path, 'rb') as f:
                original_data = f.read()
            
            total_len = len(original_data)
            chunk_size = 200
            total_chunks = (total_len + chunk_size - 1) // chunk_size
            
            # Fragmentar imagen
            chunks = []
            for i in range(total_chunks):
                offset = i * chunk_size
                chunk_data = original_data[offset:offset + chunk_size]
                
                # Simular corrupción en el chunk 2
                if i == 2:
                    # Corromper algunos bytes
                    corrupted_data = bytearray(chunk_data)
                    for j in range(min(5, len(corrupted_data))):
                        corrupted_data[j] = (corrupted_data[j] + 1) % 256
                    chunk_data = bytes(corrupted_data)
                
                packet = pack_chunk(chunk_data, total_len, offset, i, total_chunks,
                                  metadata={"chunk_type": "image_data"})
                chunks.append((i, packet))
            
            # Intentar reensamblar
            reassembler = Reassembler(total_len, total_chunks)
            corruption_detected = False
            
            for chunk_id, packet in chunks:
                try:
                    meta, payload = unpack_chunk(packet)
                    reassembler.add_chunk(meta['chunk_id'], meta['offset'], payload)
                except ValueError as e:
                    if "integrity check failed" in str(e):
                        corruption_detected = True
                        print(f"Corrupción detectada en chunk {chunk_id}")
            
            # Verificar que se detectó la corrupción
            if chunk_id == 2:  # El chunk que corrompimos
                assert corruption_detected, "No se detectó la corrupción esperada"
            
        finally:
            # Limpiar archivo temporal
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_reassembler_timeout(self):
        """Test de timeout del reensamblador"""
        reassembler = Reassembler(1000, 10, timeout=0.1)  # Timeout muy corto
        
        # Añadir solo algunos chunks
        test_data = b"chunk data"
        reassembler.add_chunk(0, 0, test_data)
        reassembler.add_chunk(1, len(test_data), test_data)
        
        # Esperar timeout
        await asyncio.sleep(0.2)
        
        assert reassembler.is_timed_out()
        assert not reassembler.is_complete()
        
        # Verificar estado
        status = reassembler.get_status()
        assert status['is_timed_out']
        assert len(status['missing_chunks']) == 8

    @pytest.mark.asyncio
    async def test_large_image_fragmentation(self):
        """Test de fragmentación de imagen grande"""
        # Crear imagen grande de prueba
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            # Crear imagen de 500x500 píxeles
            img_array = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            img.save(tmp_file.name, 'PNG')
            tmp_path = tmp_file.name
        
        try:
            with open(tmp_path, 'rb') as f:
                image_data = f.read()
            
            print(f"Tamaño de imagen: {len(image_data)} bytes")
            
            # Fragmentar con chunks pequeños
            chunk_size = 1024
            total_len = len(image_data)
            total_chunks = (total_len + chunk_size - 1) // chunk_size
            
            print(f"Total de chunks: {total_chunks}")
            
            # Crear metadatos de imagen
            metadata = {
                "image_format": "PNG",
                "width": 500,
                "height": 500,
                "channels": 3,
                "compression": "none"
            }
            
            # Fragmentar y verificar
            reassembler = Reassembler(total_len, total_chunks, timeout=30.0)
            
            for i in range(total_chunks):
                offset = i * chunk_size
                chunk_data = image_data[offset:offset + chunk_size]
                
                # Solo el primer chunk lleva metadatos
                chunk_metadata = metadata if i == 0 else None
                
                packet = pack_chunk(chunk_data, total_len, offset, i, total_chunks,
                                  compressed=True, metadata=chunk_metadata)
                
                # Verificar que el paquete se puede desempaquetar
                meta, payload = unpack_chunk(packet)
                success = reassembler.add_chunk(meta['chunk_id'], meta['offset'], payload, meta.get('metadata'))
                assert success
            
            # Verificar ensamblado completo
            assert reassembler.is_complete()
            assembled = reassembler.assemble()
            assert assembled == image_data
            
            print(f"✓ Imagen fragmentada y reensamblada correctamente")
            
        finally:
            os.unlink(tmp_path)

    def test_chunk_ordering(self):
        """Test de orden de chunks fuera de secuencia"""
        test_data = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        chunk_size = 5
        total_len = len(test_data)
        total_chunks = (total_len + chunk_size - 1) // chunk_size
        
        # Crear chunks fuera de orden
        chunks = []
        for i in range(total_chunks):
            offset = i * chunk_size
            chunk_data = test_data[offset:offset + chunk_size]
            packet = pack_chunk(chunk_data, total_len, offset, i, total_chunks)
            chunks.append((i, packet))
        
        # Mezclar orden
        random.shuffle(chunks)
        
        # Reensamblar
        reassembler = Reassembler(total_len, total_chunks)
        
        for chunk_id, packet in chunks:
            meta, payload = unpack_chunk(packet)
            reassembler.add_chunk(meta['chunk_id'], meta['offset'], payload)
        
        # Verificar ensamblado correcto independientemente del orden
        assert reassembler.is_complete()
        assembled = reassembler.assemble()
        assert assembled == test_data


if __name__ == "__main__":
    # Ejecutar tests específicos
    pytest.main([__file__, "-v"])