# Dockerización del proyecto Proyecto_Redes

Resumen rápido:

- Servicio API (FastAPI/uvicorn) disponible en http://localhost:8000
- Servicio de transporte (servidor principal) escuchando en el puerto 9000
- Servicio de imagenes (image_server) escuchando en el puerto 9001
- Frontend servido por nginx en http://localhost:5173

Archivos añadidos:

- `Dockerfile.python` — imagen base para servicios Python (API + servidores)
- `frontend/Dockerfile` — build de la SPA con Node y servido por nginx
- `frontend/nginx.conf` — configuración nginx para la SPA
- `docker-compose.yml` — orquesta servicios
- `.dockerignore` — ignora archivos innecesarios en el build

Cómo ejecutar (Windows PowerShell):

```powershell
# Construir y levantar todo
docker compose up --build

# Levantar en segundo plano
docker compose up -d --build

# Ver logs
docker compose logs -f api
```

Notas:

- El contenedor `api` expone el endpoint para subir imágenes `/upload-image` y el websocket en `/ws`.
- El frontend asume que el endpoint de la API estará disponible en `/api/` — puedes ajustar el proxy en `frontend/nginx.conf` o configurar el frontend para apuntar directamente a `http://localhost:8000`.
- Si necesitas que el servicio `transport` o `imgserver` no se ejecuten automáticamente por Docker (por ejemplo, para iniciar manualmente en modo debug), cambia el `command` en `docker-compose.yml` o comenta la sección correspondiente.
