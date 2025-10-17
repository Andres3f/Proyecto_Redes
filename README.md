# 🟢 Pasos para iniciar la interfaz web y servicios

Para que la interfaz web funcione correctamente y puedas enviar/recibir archivos e imágenes, sigue este orden recomendado:

1. **Inicia el servidor de transporte** (necesario para la transferencia de archivos e imágenes):
   ```powershell
   python ejecutar_programa.py servidor
   ```

2. **Inicia el API proxy (FastAPI)** (necesario para la interfaz web y el chat):
   ```powershell
   cd frontend_api
   pip install -r requirements.txt
   uvicorn main:app --host 127.0.0.1 --port 8000
   ```

3. **Inicia el frontend (React/Vite)**:
   ```powershell
   cd ../frontend
   npm install
   npm run dev
   ```

4. **Abre la interfaz web** en tu navegador:
   - [http://localhost:5173](http://localhost:5173)

5. **Recomendaciones y notas**:
   - Asegúrate de que los tres servicios estén corriendo antes de probar la interfaz.
   - Si vas a enviar imágenes, el backend las guarda automáticamente en la carpeta `received/` y las muestra en el chat.
   - Si tienes problemas de conexión, revisa que los puertos 9000 (servidor), 8000 (API) y 5173 (frontend) estén libres y sin bloqueos de firewall.
   - Puedes abrir dos ventanas del frontend para simular dos usuarios y probar el chat y la transferencia.

**¡Con estos pasos tendrás la interfaz y los servicios funcionando de forma óptima!**
# Proyecto de Redes - Implementación de Capas de Red

Este proyecto implementa un sistema de comunicación basado en el modelo de referencia OSI, enfocado en las capas de transporte, sesión y aplicación para transferencia confiable de archivos y mensajes de control.

## 📁 Estructura del Proyecto

```
Proyecto_Redes/
├── docs/                          # Documentación del proyecto
│   ├── especificaciones.md        # Especificaciones técnicas
│   ├── README.md                  # Documentación específica
│   └── ROADMAP.md                 # Plan de desarrollo
├── src/                           # Código fuente principal
│   ├── app/                       # Capa de aplicación
│   │   └── cliente.py             # Cliente para transferencia de archivos
│   ├── sesion/                    # Capa de sesión
│   │   ├── __init__.py
│   │   └── pruebasesion.py        # Implementación de sesiones
│   ├── transporte/                # Capa de transporte (modo confiable)
│   │   ├── __init__.py
│   │   └── reliable.py            # Protocolo confiable tipo TCP
│   ├── red/                       # Capa de red (estructura preparada)
│   │   └── __init__.py
│   └── enlace/                    # Capa de enlace (estructura preparada)
│       └── __init__.py
├── examples/                      # Ejemplos de uso
│   ├── pruebademo_mvp.py          # Demo básico servidor
│   ├── pruebademo_stream.py       # Demo de streaming
│   └── pruebdemo_img_transfer.py  # Demo transferencia de imágenes
├── tests/                         # Pruebas unitarias
│   └── test_transfer.py           # Pruebas de transferencia
├── received/                      # Directorio para archivos recibidos
├── frontend_api/                  # API proxy + WebSocket (FastAPI)
│   ├── main.py                    # Endpoint /send y /ws (chat)
│   └── test_ws_clients.py         # Script de prueba de WS (clientes simulados)
├── frontend/                      # Interfaz web (React + Vite)
│   ├── package.json
│   └── src/                       # Código fuente React
├── requirements.txt               # Dependencias del proyecto
├── ejecutar_programa.py           # EJECUTOR PRINCIPAL (RECOMENDADO)
└── README.md                      # Este archivo
```

## 🚀 Instalación y Configuración

### Requisitos Previos
- Python 3.7 o superior
- pip (gestor de paquetes de Python)

### Instalación de Dependencias

```bash
# Instalar dependencias desde requirements.txt
pip install -r requirements.txt
```

### Dependencias Principales
- `asyncio`: Para programación asíncrona
- `cryptography`: Para funciones criptográficas
- `opencv-python`: Para procesamiento de imágenes
- `pillow`: Para manipulación de imágenes
- `numpy`: Para operaciones numéricas

## 🏃‍♂️ Comandos para Ejecutar el Proyecto

## Cómo ejecutar (rápido)

Si quieres ejecutar el proyecto de forma rápida, usa los comandos siguientes en PowerShell desde la raíz del repositorio:

```powershell
# 1) Demo completo (arranca servidor y cliente, verifica transferencia)
python ejecutar_programa.py

# 2) Ejecutar solo el servidor
python ejecutar_programa.py servidor

# 3) Ejecutar solo el cliente (envía `prueba.txt` al servidor en localhost:9000)
python ejecutar_programa.py cliente

# 4) Ejecutar cliente manualmente usando la función `send_file`
$env:PYTHONPATH = "C:\Users\HP\OneDrive\Escritorio\Proyecto_Redes"
python -c "import asyncio; from src.app.cliente import send_file; asyncio.run(send_file('localhost', 9000, 'prueba.txt'))"

# 5) (Opcional) Interfaz web - iniciar proxy y frontend
cd frontend_api
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
# En otra terminal:
cd ../frontend
npm install
npm run dev
```


### ⭐ MÉTODO RECOMENDADO - Ejecutor Automático

```bash
# Demo completo (RECOMENDADO - Soluciona todos los problemas automáticamente)
python ejecutar_programa.py

# Ver todas las opciones disponibles
python ejecutar_programa.py ayuda

# Ejecutar solo servidor
python ejecutar_programa.py servidor

# Ejecutar solo cliente
python ejecutar_programa.py cliente
```

### 🖥️ Frontend (React) y proxy HTTP

Si quieres usar una interfaz web para enviar archivos, se incluye una app React mínima en `frontend/` y un pequeño proxy HTTP en `frontend_api/` que usa `src.app.cliente.send_file` para enviar archivos al servidor de transporte.

Pasos resumidos:

```powershell
# Instalar dependencias del API proxy
cd frontend_api
pip install -r requirements.txt

# Iniciar el API proxy (por defecto en http://localhost:8000)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# En otra terminal, iniciar el servidor de transporte (por ejemplo)
python ejecutar_programa.py servidor

# Instalar e iniciar la app React
cd ..\frontend
npm install
npm run dev

# Abrir http://localhost:5173 en tu navegador
```

La app sube un archivo y hace POST a `/send`. El proxy guarda temporalmente el archivo y llama a `send_file` para enviarlo al servidor de transporte (puerto 9000 por defecto).

**✅ Ventajas del ejecutor automático:**
- Configura automáticamente el entorno
- Soluciona el problema del módulo `src`
- Manejo robusto de errores
- Interfaz amigable con mensajes claros
- Verificación automática de archivos recibidos

### 🔧 Métodos Manuales (Alternativos)

#### 1. Ejecutar el Servidor (Demo MVP)
```bash
# Configurar PYTHONPATH primero
$env:PYTHONPATH = "C:\Users\HP\OneDrive\Escritorio\Proyecto_Redes"

# Ejecutar servidor
python examples/pruebademo_mvp.py
```

#### 2. Ejecutar Cliente para Enviar Archivos
```bash
# Configurar PYTHONPATH primero
$env:PYTHONPATH = "C:\Users\HP\OneDrive\Escritorio\Proyecto_Redes"

# En otra terminal, ejecutar el cliente
python -c "
import asyncio
from src.app.cliente import send_file
asyncio.run(send_file('localhost', 9000, 'prueba.txt'))
"
```

#### 3. Ejecutar Transferencia de Imágenes
```bash
# Servidor para imágenes
python examples/pruebdemo_img_transfer.py

# Cliente para enviar imágenes (en terminal separada)
python -c "
import asyncio
from src.app.cliente import send_file
asyncio.run(send_file('localhost', 9000, 'ruta/a/tu/imagen.jpg'))
"
```

### 4. Ejecutar Pruebas
```bash
# Instalar pytest si no está instalado
pip install pytest

# Ejecutar todas las pruebas
python -m pytest tests/

# Ejecutar prueba específica
python -m pytest tests/test_transfer.py -v
```

## 📋 Funcionalidades Implementadas

### Capa de Transporte (Modo Confiable)
- **Protocolo confiable tipo TCP**: Garantiza entrega ordenada de mensajes
- **Manejo de conexiones**: Gestión automática de conexiones cliente-servidor
- **Transferencia de archivos**: Soporte para archivos de hasta varios MB
- **Mensajes de control**: Sistema de mensajería para coordinación

### Capa de Sesión
- **Gestión de sesiones**: Identificación única de sesiones con UUID
- **Mensajes estructurados**: Formato JSON para comunicación
- **Control de flujo**: Manejo de diferentes tipos de mensajes

### Capa de Aplicación
- **Cliente de transferencia**: Interfaz simple para enviar archivos
- **Receptor de archivos**: Guardado automático en directorio `received/`
- **Soporte múltiples formatos**: Texto, imágenes, archivos binarios

## 🔧 Configuración del Servidor

### Puerto por Defecto
- **Puerto**: 9000
- **Host**: 0.0.0.0 (acepta conexiones desde cualquier IP)

### Cambiar Configuración
Para cambiar el puerto o host, modifica las líneas correspondientes en los archivos de ejemplo:

```python
# En examples/pruebademo_mvp.py, línea 31
await start_server("0.0.0.0", 9000, on_message)
# Cambiar 9000 por el puerto deseado
```

## 📊 Ejemplo de Uso Completo

### ⭐ Método Recomendado (Automático)
```bash
# Un solo comando ejecuta todo el demo
python ejecutar_programa.py
```

### 🔧 Método Manual
1. **Iniciar el servidor**:
   ```bash
   # Configurar PYTHONPATH primero
   $env:PYTHONPATH = "C:\Users\HP\OneDrive\Escritorio\Proyecto_Redes"
   
   # Ejecutar servidor
   python examples/pruebademo_mvp.py
   ```

2. **Enviar un archivo** (en otra terminal):
   ```bash
   # Configurar PYTHONPATH primero
   $env:PYTHONPATH = "C:\Users\HP\OneDrive\Escritorio\Proyecto_Redes"
   
   # Ejecutar cliente
   python -c "
   import asyncio
   from src.app.cliente import send_file
   asyncio.run(send_file('localhost', 9000, 'prueba.txt'))
   "
   ```

3. **Verificar recepción**:
   - El archivo se guardará en `received/prueba.txt`
   - Se mostrarán mensajes de confirmación en ambas terminales

## 🧪 Pruebas

El proyecto incluye pruebas unitarias para verificar la funcionalidad básica:

```bash
# Ejecutar todas las pruebas
python -m pytest tests/ -v

# Ejecutar con cobertura (requiere pytest-cov)
pip install pytest-cov
python -m pytest tests/ --cov=src
```

## 📚 Documentación Adicional

- **Especificaciones técnicas**: Ver `docs/especificaciones.md`
- **Plan de desarrollo**: Ver `docs/ROADMAP.md`
- **Documentación detallada**: Ver `docs/README.md`

## 🛠️ Desarrollo

### Estructura de Mensajes
Los mensajes siguen un formato JSON estándar:

```json
{
  "type": "control|file",
  "msg": "mensaje de control",
  "name": "nombre_archivo.txt",
  "size": 1024
}
```

### Agregar Nuevas Funcionalidades
1. Implementar en la capa correspondiente (`src/`)
2. Crear ejemplo en `examples/`
3. Agregar pruebas en `tests/`
4. Actualizar documentación

## 🆘 Solución de Problemas

### ❌ Error: "ModuleNotFoundError: No module named 'src'"

**Solución rápida:**
```bash
# Usar el ejecutor automático (recomendado)
python ejecutar_programa.py
```

**Solución manual:**
```bash
# Configurar PYTHONPATH antes de ejecutar
$env:PYTHONPATH = "C:\Users\HP\OneDrive\Escritorio\Proyecto_Redes"
python examples/pruebademo_mvp.py
```

### ❌ Error: "ConnectionRefusedError"

**Causa:** El servidor no está ejecutándose.

**Solución:**
1. Ejecutar el servidor primero
2. Esperar a que inicie completamente
3. Luego ejecutar el cliente

### ✅ Verificar que todo funciona

```bash
# Ejecutar demo completo para verificar
python ejecutar_programa.py
```

**🚀 Recomendación**: Usa `python ejecutar_programa.py` para una experiencia sin problemas.

