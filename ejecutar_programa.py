#!/usr/bin/env python3
"""
Script ejecutor completo para el proyecto de redes
Soluciona automáticamente el problema del módulo 'src' y ejecuta el programa
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Configurar el path para que Python encuentre el módulo 'src'
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Importar módulos del proyecto
from src.transporte.reliable import start_server
from src.app.cliente import send_file

class ProgramaRedes:
    def __init__(self):
        self.archivo_prueba = "prueba.txt"
        self.directorio_recibidos = Path("received")
        self.directorio_recibidos.mkdir(exist_ok=True)
        
    async def manejar_mensaje_servidor(self, data, writer, transport=None):
        """Maneja los mensajes recibidos en el servidor"""
        try:
            # Intentar decodificar como JSON (mensaje de control)
            packet = json.loads(data.decode('utf-8'))
            
            if packet.get("type") == "control":
                print(f"[Servidor] Control: {packet['msg']}")
                
            elif packet.get("type") == "file":
                nombre_archivo = packet.get("name", "archivo_recibido.bin")
                tamaño = packet.get("size", 0)
                print(f"[Servidor] Recibiendo archivo: {nombre_archivo} ({tamaño} bytes)")
                
                # Esperar los datos reales del archivo
                from src.transporte.reliable import read_message
                try:
                    datos_archivo = await read_message(writer._transport._protocol._stream_reader)
                    ruta_archivo = self.directorio_recibidos / nombre_archivo
                    ruta_archivo.write_bytes(datos_archivo)
                    print(f"[Servidor] Archivo guardado: {ruta_archivo}")
                except Exception as e:
                    print(f"[Servidor] Error al leer datos del archivo: {e}")
                    
        except json.JSONDecodeError:
            # Si no es JSON, probablemente son datos binarios del archivo
            print(f"[Servidor] Datos binarios recibidos ({len(data)} bytes)")
            
        except UnicodeDecodeError:
            # Datos binarios que no se pueden decodificar como UTF-8
            print(f"[Servidor] Datos binarios recibidos ({len(data)} bytes)")
            
        except Exception as e:
            print(f"[Servidor] Error procesando mensaje: {e}")

    async def ejecutar_servidor(self, host="127.0.0.1", puerto=9000):
        """Ejecuta el servidor"""
        print(f"[Servidor] Iniciando en {host}:{puerto}...")
        try:
            await start_server(host, puerto, self.manejar_mensaje_servidor)
        except Exception as e:
            print(f"[Servidor] Error: {e}")

    async def ejecutar_cliente(self, host="127.0.0.1", puerto=9000, archivo=None):
        """Ejecuta el cliente para enviar un archivo"""
        if archivo is None:
            archivo = self.archivo_prueba
            
        if not os.path.exists(archivo):
            print(f"[Cliente] Archivo no encontrado: {archivo}")
            return False
            
        print(f"[Cliente] Enviando archivo: {archivo}")
        try:
            await send_file(host, puerto, archivo)
            print("[Cliente] Archivo enviado exitosamente!")
            return True
        except Exception as e:
            print(f"[Cliente] Error: {e}")
            return False

    async def demo_completo(self):
        """Ejecuta una demostración completa del programa"""
        print("=" * 50)
        print("PROYECTO DE REDES - DEMO COMPLETO")
        print("=" * 50)
        print()
        
        # Verificar que el archivo de prueba existe
        if not os.path.exists(self.archivo_prueba):
            print(f"Creando archivo de prueba: {self.archivo_prueba}")
            with open(self.archivo_prueba, 'w', encoding='utf-8') as f:
                f.write("Hola Mundo!\nEste es un archivo de prueba para el proyecto de redes.")
        
        print("1. Iniciando servidor...")
        
        # Crear tarea del servidor
        servidor_task = asyncio.create_task(self.ejecutar_servidor())
        
        # Esperar a que el servidor se inicie
        await asyncio.sleep(2)
        
        print("2. Ejecutando cliente...")
        
        # Ejecutar cliente
        exito = await self.ejecutar_cliente()
        
        if exito:
            print("3. Verificando archivo recibido...")
            archivo_recibido = self.directorio_recibidos / self.archivo_prueba
            if archivo_recibido.exists():
                tamaño = archivo_recibido.stat().st_size
                print(f"Archivo recibido: {archivo_recibido} ({tamaño} bytes)")
            else:
                print("Archivo no encontrado en directorio recibidos")
        
        # Cancelar servidor
        print("4. Cerrando servidor...")
        servidor_task.cancel()
        try:
            await servidor_task
        except asyncio.CancelledError:
            pass
        
        print()
        print("Demo completado exitosamente!")
        print(f"Archivos recibidos en: {self.directorio_recibidos.absolute()}")
        print("=" * 50)

    def mostrar_ayuda(self):
        """Muestra la ayuda del programa"""
        print("=" * 60)
        print("PROYECTO DE REDES - EJECUTOR")
        print("=" * 60)
        print()
        print("Uso:")
        print("  python ejecutar_programa.py [comando]")
        print()
        print("Comandos disponibles:")
        print("  demo        - Ejecuta demostración completa (por defecto)")
        print("  servidor    - Ejecuta solo el servidor")
        print("  cliente     - Ejecuta solo el cliente")
        print("  ayuda       - Muestra esta ayuda")
        print()
        print("Ejemplos:")
        print("  python ejecutar_programa.py")
        print("  python ejecutar_programa.py demo")
        print("  python ejecutar_programa.py servidor")
        print("  python ejecutar_programa.py cliente")
        print("=" * 60)

async def main():
    """Función principal"""
    programa = ProgramaRedes()
    
    # Obtener comando de los argumentos
    comando = sys.argv[1] if len(sys.argv) > 1 else "demo"
    
    try:
        if comando == "demo":
            await programa.demo_completo()
            
        elif comando == "servidor":
            print("Ejecutando servidor...")
            await programa.ejecutar_servidor()
            
        elif comando == "cliente":
            print("Ejecutando cliente...")
            await programa.ejecutar_cliente()
            
        elif comando == "ayuda":
            programa.mostrar_ayuda()
            
        else:
            print(f"Comando desconocido: {comando}")
            programa.mostrar_ayuda()
            
    except KeyboardInterrupt:
        print("\nPrograma interrumpido por el usuario")
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    # Configurar el PYTHONPATH automáticamente
    os.environ['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))
    
    # Ejecutar el programa
    asyncio.run(main())
