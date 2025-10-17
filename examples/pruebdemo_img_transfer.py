import asyncio
import os
import random
import time
import json
from typing import Dict, Optional
from PIL import Image
import io

from src.transporte.reliable import start_server, send_message, read_message, ReliableTransport, ReliableConfig
from src.transporte.fragmentation import pack_chunk, unpack_chunk, Reassembler

RECV_DIR = os.path.join(os.path.dirname(__file__), '..', 'received')
os.makedirs(RECV_DIR, exist_ok=True)

# Configuraciones de rendimiento
PERFORMANCE_REPORT = {
    "transfers": [],
    "start_time": None,
    "end_time": None
}

def _validate_complete_image(filepath: str) -> bool:
    """Valida que una imagen completa se pueda abrir correctamente"""
    try:
        with Image.open(filepath) as img:
            img.verify()  # Verificar integridad
        print(f"[VALIDATION] ✓ Imagen válida: {os.path.basename(filepath)}")
        return True
    except Exception as e:
        print(f"[VALIDATION] ✗ Imagen inválida: {e}")
        return False

def _validate_partial_image(filepath: str, expected_size: int) -> bool:
    """Valida una imagen parcial y proporciona estadísticas"""
    try:
        file_size = os.path.getsize(filepath)
        completion = (file_size / expected_size) * 100 if expected_size > 0 else 0
        
        print(f"[VALIDATION] Imagen parcial: {completion:.1f}% completa ({file_size}/{expected_size} bytes)")
        
        # Intentar abrir como imagen para ver si es parcialmente válida
        try:
            with Image.open(filepath) as img:
                print(f"[VALIDATION] ✓ Imagen parcial reconocible: {img.format} {img.size}")
                return True
        except Exception:
            print(f"[VALIDATION] - Imagen parcial no reconocible como formato válido")
            return False
            
    except Exception as e:
        print(f"[VALIDATION] Error validando imagen parcial: {e}")
        return False


async def handle_client(reader, writer, mode='FIABLE', loss_rate=0.0, enable_fec=False):
    """
    Maneja cliente con soporte mejorado para FIABLE y SEMI-FIABLE con FEC simulado
    """
    peer = writer.get_extra_info('peername')
    print(f"[IMG SERVER] Conexión de {peer} - Modo: {mode}, Pérdida: {loss_rate*100:.1f}%")
    
    start_time = time.time()
    chunks_received = 0
    chunks_lost = 0
    
    try:
        # Leer control/meta
        ctrl = await read_message(reader)
        meta = await read_message(reader)
        meta_obj = json.loads(meta)
        
        if meta_obj.get('type') != 'img_meta':
            print("[IMG SERVER] Meta inesperado")
            return
            
        name = meta_obj['name']
        size = meta_obj['size']
        total_chunks = meta_obj['total_chunks']
        image_format = meta_obj.get('format', 'unknown')
        
        print(f"[IMG SERVER] Recibiendo {name} ({image_format})")
        print(f"              Tamaño: {size} bytes, Chunks: {total_chunks}")

        # Timeout más largo para imágenes grandes
        timeout = max(10.0, total_chunks * 0.1)
        reassembler = Reassembler(size, total_chunks, timeout=timeout)
        
        # Recibir chunks
        last_progress = 0
        while True:
            try:
                pkt = await read_message(reader)
            except Exception:
                break
                
            # Simular pérdida de paquetes en modo SEMI-FIABLE
            if mode == 'SEMI-FIABLE' and random.random() < loss_rate:
                chunks_lost += 1
                continue
                
            try:
                meta_c, payload = unpack_chunk(pkt)
                chunks_received += 1
                
                # Añadir chunk con metadatos
                success = reassembler.add_chunk(
                    meta_c['chunk_id'], 
                    meta_c['offset'], 
                    payload, 
                    meta_c.get('metadata')
                )
                
                if success:
                    # Mostrar progreso
                    progress = reassembler.get_progress()
                    if progress - last_progress >= 10:  # Cada 10%
                        print(f"[IMG SERVER] Progreso: {progress:.1f}%")
                        last_progress = progress
                
                # Enviar ACK en modo FIABLE
                if mode == 'FIABLE':
                    ack = json.dumps({
                        "type": "ack", 
                        "chunk_id": meta_c['chunk_id'],
                        "timestamp": time.time()
                    }).encode()
                    await send_message(writer, ack)
                    
                if reassembler.is_complete():
                    break
                    
            except ValueError as e:
                print(f"[IMG SERVER] Error en chunk: {e}")
                chunks_lost += 1

        # Estadísticas de transferencia
        end_time = time.time()
        transfer_time = end_time - start_time
        
        print(f"[IMG SERVER] Transferencia completada en {transfer_time:.2f}s")
        print(f"              Chunks recibidos: {chunks_received}/{total_chunks}")
        print(f"              Chunks perdidos: {chunks_lost}")
        
        # Intentar ensamblar
        assembled = reassembler.assemble()
        out_path = os.path.join(RECV_DIR, name)
        
        if assembled is None:
            # Imagen parcial: usar FEC simulado o guardar parcial
            if enable_fec and mode == 'SEMI-FIABLE':
                print("[IMG SERVER] Aplicando FEC simulado...")
                # Simular reconstrucción con códigos de corrección
                partial_data = reassembler.assemble_partial()
                if partial_data:
                    with open(out_path + '.fec_recovered', 'wb') as f:
                        f.write(partial_data)
                    print(f"[IMG SERVER] Imagen recuperada con FEC: {out_path}.fec_recovered")
                    _validate_partial_image(out_path + '.fec_recovered', size)
            else:
                # Guardar imagen parcial
                partial_data = reassembler.assemble_partial()
                with open(out_path + '.partial', 'wb') as f:
                    f.write(partial_data)
                print(f"[IMG SERVER] Imagen parcial guardada: {out_path}.partial")
                _validate_partial_image(out_path + '.partial', size)
        else:
            # Imagen completa
            with open(out_path, 'wb') as f:
                f.write(assembled)
            print(f"[IMG SERVER] ✓ Imagen completa guardada: {out_path}")
            _validate_complete_image(out_path)
        
        # Registrar estadísticas de rendimiento
        PERFORMANCE_REPORT["transfers"].append({
            "filename": name,
            "size": size,
            "chunks": total_chunks,
            "mode": mode,
            "loss_rate": loss_rate,
            "transfer_time": transfer_time,
            "chunks_received": chunks_received,
            "chunks_lost": chunks_lost,
            "success_rate": chunks_received / (chunks_received + chunks_lost) if (chunks_received + chunks_lost) > 0 else 0,
            "throughput_bps": size / transfer_time if transfer_time > 0 else 0,
            "complete": assembled is not None
        })

    finally:
        writer.close()
        await writer.wait_closed()


async def client_send_image(host, port, filepath, mode='FIABLE', loss_rate=0.0, 
                           chunk_size=1024, max_retries=5, ack_timeout=1.0, enable_compression=True):
    """
    Cliente mejorado para envío de imágenes con soporte completo para ambos modos
    """
    start_time = time.time()
    
    reader, writer = await asyncio.open_connection(host, port)
    name = os.path.basename(filepath)
    
    # Leer datos de imagen
    with open(filepath, 'rb') as f:
        data = f.read()
    
    total_len = len(data)
    total_chunks = (total_len + chunk_size - 1) // chunk_size
    
    # Detectar formato de imagen
    image_format = "unknown"
    try:
        with Image.open(filepath) as img:
            image_format = img.format.lower()
            img_info = {
                "width": img.width,
                "height": img.height,
                "mode": img.mode
            }
    except Exception:
        img_info = {}
    
    print(f"[CLIENT] Enviando {name} ({image_format})")
    print(f"         Tamaño: {total_len} bytes, Chunks: {total_chunks}")
    print(f"         Modo: {mode}, Chunk size: {chunk_size}")
    
    # Enviar control y metadatos
    ctrl = {"type": "control", "msg": f"send image {name}"}
    await send_message(writer, json.dumps(ctrl).encode())
    
    meta = {
        "type": "img_meta", 
        "name": name, 
        "size": total_len, 
        "total_chunks": total_chunks,
        "format": image_format,
        "chunk_size": chunk_size,
        **img_info
    }
    await send_message(writer, json.dumps(meta).encode())

    # Estadísticas de envío
    chunks_sent = 0
    chunks_acked = 0
    total_retries = 0
    
    # Enviar chunks
    for i in range(total_chunks):
        offset = i * chunk_size
        part = data[offset:offset + chunk_size]
        
        # Metadatos específicos del chunk (solo para el primero)
        chunk_metadata = None
        if i == 0:
            chunk_metadata = {
                "image_format": image_format,
                "total_size": total_len,
                "compression_enabled": enable_compression
            }
        
        # Crear paquete con compresión opcional
        pkt = pack_chunk(part, total_len, offset, i, total_chunks, 
                        compressed=enable_compression, metadata=chunk_metadata)
        
        if mode == 'FIABLE':
            # Modo confiable con ACK y reintentos
            retries = 0
            ack_received = False
            
            while retries < max_retries and not ack_received:
                await send_message(writer, pkt)
                chunks_sent += 1
                
                try:
                    # Esperar ACK con timeout
                    ack_raw = await asyncio.wait_for(read_message(reader), timeout=ack_timeout)
                    ack = json.loads(ack_raw)
                    
                    if ack.get('type') == 'ack' and ack.get('chunk_id') == i:
                        chunks_acked += 1
                        ack_received = True
                    
                except asyncio.TimeoutError:
                    retries += 1
                    total_retries += 1
                    print(f"[CLIENT] Timeout chunk {i}, reintento {retries}/{max_retries}")
                except Exception as e:
                    print(f"[CLIENT] Error esperando ACK chunk {i}: {e}")
                    retries += 1
                    total_retries += 1
            
            if not ack_received:
                print(f"[CLIENT] ✗ Chunk {i} falló tras {max_retries} intentos")
        else:
            # Modo SEMI-FIABLE: enviar una vez (el servidor simula pérdidas)
            await send_message(writer, pkt)
            chunks_sent += 1
        
        # Mostrar progreso cada 10%
        if (i + 1) % max(1, total_chunks // 10) == 0:
            progress = ((i + 1) / total_chunks) * 100
            print(f"[CLIENT] Enviado: {progress:.1f}%")

    # Estadísticas finales
    end_time = time.time()
    transfer_time = end_time - start_time
    
    print(f"[CLIENT] Transferencia completada en {transfer_time:.2f}s")
    print(f"         Chunks enviados: {chunks_sent}")
    if mode == 'FIABLE':
        print(f"         ACKs recibidos: {chunks_acked}/{total_chunks}")
        print(f"         Reintentos totales: {total_retries}")
    
    writer.close()
    await writer.wait_closed()
    
    return {
        "chunks_sent": chunks_sent,
        "chunks_acked": chunks_acked,
        "total_retries": total_retries,
        "transfer_time": transfer_time,
        "throughput": total_len / transfer_time if transfer_time > 0 else 0
    }


async def run_demo(image_path, mode='FIABLE', loss_rate=0.1, chunk_size=1024, enable_fec=False):
    """
    Ejecuta demo completo con informe de rendimiento
    """
    PERFORMANCE_REPORT["start_time"] = time.time()
    
    print(f"\n{'='*60}")
    print(f"DEMO TRANSFERENCIA DE IMÁGENES")
    print(f"{'='*60}")
    print(f"Archivo: {os.path.basename(image_path)}")
    print(f"Modo: {mode}")
    print(f"Tasa de pérdida: {loss_rate*100:.1f}%")
    print(f"Tamaño de chunk: {chunk_size} bytes")
    print(f"FEC habilitado: {enable_fec}")
    print(f"{'='*60}\n")
    
    # Iniciar servidor
    srv = await asyncio.start_server(
        lambda r, w: handle_client(r, w, mode, loss_rate, enable_fec), 
        '127.0.0.1', 0
    )
    host, port = srv.sockets[0].getsockname()
    print(f"[SERVER] Servidor iniciado en {host}:{port}\n")

    # Ejecutar cliente
    try:
        client_stats = await client_send_image(
            host, port, image_path, mode, loss_rate, 
            chunk_size=chunk_size, enable_compression=True
        )
        
        # Esperar un poco para que el servidor termine de procesar
        await asyncio.sleep(1)
        
    finally:
        srv.close()
        await srv.wait_closed()
    
    PERFORMANCE_REPORT["end_time"] = time.time()
    
    # Generar informe de rendimiento
    _generate_performance_report()

def _generate_performance_report():
    """Genera informe detallado de rendimiento"""
    print(f"\n{'='*60}")
    print(f"INFORME DE RENDIMIENTO")
    print(f"{'='*60}")
    
    if not PERFORMANCE_REPORT["transfers"]:
        print("No se registraron transferencias.")
        return
    
    total_time = PERFORMANCE_REPORT["end_time"] - PERFORMANCE_REPORT["start_time"]
    print(f"Tiempo total de demo: {total_time:.2f}s\n")
    
    for i, transfer in enumerate(PERFORMANCE_REPORT["transfers"], 1):
        print(f"Transferencia {i}: {transfer['filename']}")
        print(f"  Tamaño: {transfer['size']:,} bytes")
        print(f"  Chunks: {transfer['chunks_received']}/{transfer['chunks']} recibidos")
        print(f"  Perdidos: {transfer['chunks_lost']}")
        print(f"  Modo: {transfer['mode']}")
        print(f"  Tasa de pérdida configurada: {transfer['loss_rate']*100:.1f}%")
        print(f"  Tasa de éxito real: {transfer['success_rate']*100:.1f}%")
        print(f"  Tiempo de transferencia: {transfer['transfer_time']:.2f}s")
        print(f"  Throughput: {transfer['throughput_bps']/1024:.1f} KB/s")
        print(f"  Completa: {'✓' if transfer['complete'] else '✗'}")
        print()
    
    # Estadísticas agregadas
    total_bytes = sum(t['size'] for t in PERFORMANCE_REPORT["transfers"])
    total_chunks = sum(t['chunks'] for t in PERFORMANCE_REPORT["transfers"])
    total_received = sum(t['chunks_received'] for t in PERFORMANCE_REPORT["transfers"])
    total_lost = sum(t['chunks_lost'] for t in PERFORMANCE_REPORT["transfers"])
    
    print("RESUMEN AGREGADO:")
    print(f"  Total bytes transferidos: {total_bytes:,}")
    print(f"  Total chunks: {total_received}/{total_chunks} ({(total_received/total_chunks)*100:.1f}%)")
    print(f"  Total perdidos: {total_lost}")
    print(f"  Throughput promedio: {(total_bytes/total_time)/1024:.1f} KB/s")
    print(f"{'='*60}\n")

async def run_performance_benchmark(image_paths, chunk_sizes=[512, 1024, 2048], loss_rates=[0.0, 0.1, 0.3]):
    """
    Ejecuta benchmark completo de rendimiento con múltiples configuraciones
    """
    print("INICIANDO BENCHMARK DE RENDIMIENTO")
    print("="*60)
    
    for image_path in image_paths:
        if not os.path.exists(image_path):
            print(f"⚠️  Archivo no encontrado: {image_path}")
            continue
            
        for chunk_size in chunk_sizes:
            for loss_rate in loss_rates:
                for mode in ['FIABLE', 'SEMI-FIABLE']:
                    print(f"\nTesting: {os.path.basename(image_path)} - {mode} - chunk:{chunk_size} - loss:{loss_rate*100:.0f}%")
                    try:
                        await run_demo(image_path, mode, loss_rate, chunk_size)
                        await asyncio.sleep(0.5)  # Pausa entre tests
                    except Exception as e:
                        print(f"❌ Error en test: {e}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        # Iniciar solo el servidor en el puerto 9000 y dejarlo escuchando indefinidamente
        import asyncio
        print("Iniciando servidor de imágenes en 127.0.0.1:9000 ...")
        async def main():
            server = await asyncio.start_server(
                lambda r, w: handle_client(r, w, mode='FIABLE', loss_rate=0.0, enable_fec=False),
                '127.0.0.1', 9000
            )
            async with server:
                await server.serve_forever()
        asyncio.run(main())
    else:
        if len(sys.argv) < 2:
            print('Uso: python pruebdemo_img_transfer.py <image_path> [modo] [loss_rate] [chunk_size] [--benchmark]')
            print('')
            print('Parámetros:')
            print('  image_path  : Ruta al archivo de imagen (PNG/JPEG)')
            print('  modo        : FIABLE (default) | SEMI-FIABLE')
            print('  loss_rate   : Tasa de pérdida 0.0-1.0 (default: 0.1)')
            print('  chunk_size  : Tamaño de chunk en bytes (default: 1024)')
            print('  --benchmark : Ejecutar benchmark completo')
            print('')
            print('Ejemplos:')
            print('  python pruebdemo_img_transfer.py imagen.png')
            print('  python pruebdemo_img_transfer.py imagen.jpg SEMI-FIABLE 0.2 512')
            print('  python pruebdemo_img_transfer.py imagen.png --benchmark')
            sys.exit(1)
        path = sys.argv[1]
        if '--benchmark' in sys.argv:
            # Ejecutar benchmark completo
            asyncio.run(run_performance_benchmark([path]))
        else:
            # Ejecutar demo individual
            mode = sys.argv[2] if len(sys.argv) > 2 else 'FIABLE'
            lr = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1
            cs = int(sys.argv[4]) if len(sys.argv) > 4 else 1024
            enable_fec = '--fec' in sys.argv
            asyncio.run(run_demo(path, mode, lr, chunk_size=cs, enable_fec=enable_fec))
