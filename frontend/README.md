# Frontend para Proyecto_Redes

Aplicación React minimal que incluye ahora una interfaz de chat WebSocket y la funcionalidad previa de envío de archivos mediante `frontend_api`.

Pasos rápidos (chat):

1. Instalar dependencias del API y del frontend:

```powershell
# En una terminal: instalar dependencias Python y arrancar el API
cd frontend_api
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000

# En otra terminal: instalar dependencias JS e iniciar la app React
cd ..\frontend
npm install
npm run dev
```

2. Abrir la app en el navegador (por defecto Vite usa http://localhost:5173). En dos pestañas distintas:
	- En cada pestaña introduce un nombre diferente (por ejemplo `alice` y `bob`) y pulsa "Conectar".
	- La lista de usuarios conectados se actualiza automáticamente.
	- Selecciona un usuario en la lista, escribe un mensaje y pulsa "Enviar". El mensaje debe llegar al destinatario.

3. Prueba automática (sin navegador): hay un script de prueba en `frontend_api/test_ws_clients.py` que simula dos clientes y demuestra intercambio de mensajes.

Notas adicionales:
- El endpoint WebSocket es `ws://localhost:8000/ws`.
- Protocolo (JSON):
	- Registro: {"type":"register","username":"alice"}
	- Enviar mensaje: {"type":"message","to":"bob","msg":"hola"}
	- Solicitar lista: {"type":"list"}

- Mensajes no entregados se almacenan en memoria en `frontend_api` y se entregan al reconectar el usuario. Esto es simple y no persistente.

Si quieres que implemente confirmaciones de entrega, persistencia o envío de archivos dentro del chat (por ejemplo dividir en chunks), dime cuál de estas mejoras prefieres y lo implemento a continuación.
