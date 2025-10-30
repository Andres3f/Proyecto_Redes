# Proyecto Redes - Sistema de Transferencia de Archivos

Sistema de transferencia de archivos con arquitectura cliente-servidor. Implementa chat en tiempo real y transferencia de archivos con fragmentación. Completamente containerizado con Docker.

## Estructura del Proyecto

```
.
├── docker-compose.yml              # Configuración de servicios Docker
├── Dockerfile.python              # Dockerfile para servicios Python
├── ejecutar_programa.py           # Script principal del servidor
├── image_server.py                # Servidor de imágenes
├── requirements.txt               # Dependencias Python
├── frontend/                      # Interfaz web (React)
│   ├── Dockerfile
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── LayerVisualization.jsx
│   │   │   ├── Toast.jsx
│   │   │   └── Tooltip.jsx
│   │   ├── design-system.jsx
│   │   └── styles_new.css
│   ├── index.html
│   └── nginx.conf
├── frontend_api/                  # API FastAPI
│   ├── main.py
│   └── requirements.txt
├── src/                          # Código fuente
│   ├── app/
│   │   └── cliente.py
│   ├── enlace/
│   ├── red/
│   ├── sesion/
│   └── transporte/
│       ├── fragmentation.py
│       └── reliable.py
└── tests/                        # Pruebas unitarias
    ├── test_fragmentation.py
    └── test_transfer.py
```

## Requisitos

- Docker
- Docker Compose
- Cuenta de Ngrok

## Uso con Docker

### Ejecucion Local

1. Clonar el repositorio:
```bash
git clone https://github.com/Andres3f/Proyecto_Redes.git
cd Proyecto_Redes
```

2. Iniciar todos los servicios:
```bash
docker compose up --build
```

3. Acceder a la aplicacion:
```
http://localhost:5173
```

### Ejecucion en Red Local (Multiples Maquinas)

1. Acceder a la aplicacion:
```
https://unrendered-spectacularly-rihanna.ngrok-free.dev/

```

### Detener los Servicios

```bash
docker compose down
```

## Servicios

### Frontend
- Interfaz web construida con React y Vite
- Sistema de notificaciones Toast
- Tooltips interactivos
- Tema claro/oscuro
- Puerto: 5173

### Frontend API
- Implementado con FastAPI
- Comunicacion WebSocket para chat en tiempo real
- Gestion de transferencia y almacenamiento de archivos
- Puerto: 8000

### Servidor de Transporte
- Capa de transporte confiable
- Fragmentacion y reensamblaje de archivos
- Control de flujo y confiabilidad
- Puerto: 9000

### Servidor de Imagenes
- Almacenamiento y gestion de imagenes transferidas
- Servidor HTTP para archivos recibidos
- Puerto: 9001

## Funcionalidades

- Chat en tiempo real entre multiples usuarios
- Transferencia de archivos con fragmentacion automatica
- Dos modos de transferencia:
  - FIABLE: Garantiza entrega completa con ACKs y reintentos
  - SEMI-FIABLE: Envio rapido sin confirmaciones
- Visualizacion de capas de red en tiempo real
- Soporte para imagenes y archivos de texto
- Interfaz web responsiva con tema claro/oscuro
- Sistema de notificaciones

## Puertos Utilizados

| Servicio | Puerto | Descripcion |
|----------|--------|-------------|
| Frontend | 5173 | Interfaz web React |
| Frontend API | 8000 | API WebSocket y HTTP |
| Transporte | 9000 | Servidor de transporte |
| Imagenes | 9001 | Servidor de archivos |
