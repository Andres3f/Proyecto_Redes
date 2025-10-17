import React, { useState, useRef, useEffect } from 'react'
import './styles.css'

export default function App() {
  // Estados para chat (manteniendo el diseño original)
  const [username, setUsername] = useState('')
  const [connected, setConnected] = useState(false)
  const [socket, setSocket] = useState(null)
  // Cambiamos a un objeto: { usuario: [ {from, to, content} ] }
  const [chatHistory, setChatHistory] = useState({})
  // Estado para mensajes no leídos: { usuario: cantidad }
  const [unread, setUnread] = useState({})
  const [users, setUsers] = useState([])
  const [newMessage, setNewMessage] = useState('')
  const [selectedUser, setSelectedUser] = useState('')

  // Estados para funcionalidad de imágenes y modo de envío
  const [uploadStatus, setUploadStatus] = useState('')
  const [transferStats, setTransferStats] = useState(null)
  const [transferMode, setTransferMode] = useState('FIABLE')
  const fileInputRef = useRef(null)
  
  // Conectar WebSocket
  const connectWebSocket = () => {
    if (username.trim()) {
      const ws = new WebSocket('ws://localhost:8000/ws')
      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'register', username }))
        ws.send(JSON.stringify({ type: 'list' }))
        setConnected(true)
        setSocket(ws)
      }
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'message') {
          // Determinar el otro usuario de la conversación
          const from = data.from || data.username || 'Desconocido'
          const to = data.to || username
          const otherUser = from === username ? to : from
          setChatHistory(prev => {
            const prevMsgs = prev[otherUser] || []
            return {
              ...prev,
              [otherUser]: [...prevMsgs, {
                from,
                to,
                content: data.msg || data.content || ''
              }]
            }
          })
          // Si el mensaje es recibido (no enviado por mí) y no estoy en ese chat, marcar como no leído
          if (from !== username && selectedUser !== from) {
            setUnread(prev => ({
              ...prev,
              [from]: (prev[from] || 0) + 1
            }))
          }
        } else if (data.type === 'list' || data.type === 'user_list') {
          setUsers(data.users || [])
        }
      }
      ws.onclose = () => {
        setConnected(false)
        setSocket(null)
      }
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    }
  }
  
  // Desconectar WebSocket
  const disconnectWebSocket = () => {
    if (socket) {
      socket.close()
    }
  }
  
  // Actualizar lista de usuarios periódicamente
  useEffect(() => {
    if (!socket || !connected) return
    const interval = setInterval(() => {
      socket.send(JSON.stringify({ type: 'list' }))
    }, 2000)
    return () => clearInterval(interval)
  }, [socket, connected])
  
  // Enviar mensaje SOLO al usuario seleccionado
  const sendMessage = () => {
    if (socket && newMessage.trim() && selectedUser) {
      // Enviar por WebSocket
      socket.send(JSON.stringify({
        type: 'message',
        to: selectedUser,
        msg: newMessage
      }))
      // Mostrarlo inmediatamente en el historial local
      setChatHistory(prev => {
        const prevMsgs = prev[selectedUser] || []
        return {
          ...prev,
          [selectedUser]: [...prevMsgs, {
            from: username,
            to: selectedUser,
            content: newMessage
          }]
        }
      })
      setNewMessage('')
    }
  }
  
  // Limpiar al desmontar
  useEffect(() => {
    return () => {
      if (socket) {
        socket.close()
      }
    }
  }, [socket])
  
  const uploadImage = async (file) => {
    if (!file || !selectedUser) return
    const formData = new FormData()
  formData.append('file', file)
  formData.append('transfer_mode', transferMode)
  formData.append('chunk_size', '4096')
  formData.append('max_retries', '3')
    try {
      setUploadStatus('Subiendo imagen...')
      const response = await fetch('http://localhost:8000/upload-image', {
        method: 'POST',
        body: formData
      })
      const result = await response.json()
      if (result.status === 'sent') {
        setUploadStatus(`✅ Imagen enviada: ${result.filename}`)
        setTransferStats(result.stats)
        // Enviar mensaje de imagen al usuario seleccionado
        if (socket) {
          // Suponiendo que el backend guarda la imagen en /received/<filename>
          if (!result.filename) {
            setUploadStatus('❌ Error: No se recibió el nombre seguro del archivo.');
            setTimeout(() => setUploadStatus(''), 5000);
            return;
          }
          const imageUrl = `http://localhost:8000/received/${result.filename}`
          const imageMsg = `<img src='${imageUrl}' alt='imagen' style='max-width:200px;max-height:200px;' />`
          socket.send(JSON.stringify({
            type: 'message',
            to: selectedUser,
            msg: imageMsg
          }))
          // Mostrarlo inmediatamente en el historial local
          setChatHistory(prev => {
            const prevMsgs = prev[selectedUser] || []
            return {
              ...prev,
              [selectedUser]: [...prevMsgs, {
                from: username,
                to: selectedUser,
                content: imageMsg
              }]
            }
          })
        }
        setTimeout(() => setUploadStatus(''), 3000)
      } else {
        setUploadStatus(`❌ Error: ${result.error || 'No se pudo enviar la imagen.'}`)
        setTimeout(() => setUploadStatus(''), 5000)
      }
    } catch (error) {
      setUploadStatus(`❌ Error: ${error.message}`)
      setTimeout(() => setUploadStatus(''), 5000)
    }
  }
  
  // Manejar selección de usuario: limpiar no leídos
  const handleSelectUser = (user) => {
    setSelectedUser(user)
    setUnread(prev => {
      const copy = { ...prev }
      copy[user] = 0
      return copy
    })
  }
  // Manejar selección de archivo
  const handleFileSelect = (event) => {
    const file = event.target.files[0]
    if (file) {
      uploadImage(file)
    }
  }
  
  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Chat — Proyecto Redes</h1>
      {!connected ? (
        <div style={{ marginBottom: '20px' }}>
          <input
            type="text"
            placeholder="Tu nombre de usuario"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && connectWebSocket()}
            style={{ padding: '8px', marginRight: '10px', fontSize: '14px' }}
          />
          <button onClick={connectWebSocket} style={{ padding: '8px 16px' }}>
            Conectar
          </button>
        </div>
      ) : (
        <div style={{ marginBottom: '20px' }}>
          <span>Conectado como <strong>{username}</strong></span>
          <button 
            onClick={disconnectWebSocket} 
            style={{ marginLeft: '10px', padding: '4px 12px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px' }}
          >
            Desconectar
          </button>
        </div>
      )}
      <div style={{ display: 'flex', gap: '20px' }}>
        {/* Mensajes */}
        <div style={{ flex: 2 }}>
          <h3>Mensajes</h3>
          <div style={{ border: '1px solid #ccc', padding: '10px', height: '300px', overflowY: 'auto', backgroundColor: '#f9f9f9' }}>
            {/* Mostrar solo la conversación con el usuario seleccionado */}
            {selectedUser && chatHistory[selectedUser] && chatHistory[selectedUser].length > 0 ? (
              chatHistory[selectedUser].map((msg, index) => (
                <div key={index} style={{ marginBottom: '8px', textAlign: msg.from === username ? 'right' : 'left' }}>
                  <span style={{ fontWeight: msg.from === username ? 'bold' : 'normal', color: msg.from === username ? '#007bff' : '#333' }}>
                    {msg.from === username ? 'Tú' : msg.from}:
                  </span>{' '}
                  <span dangerouslySetInnerHTML={{ __html: msg.content }} />
                </div>
              ))
            ) : (
              <div style={{ color: '#aaa', textAlign: 'center', marginTop: '40px' }}>
                {selectedUser ? 'No hay mensajes con este usuario.' : 'Selecciona un usuario para chatear.'}
              </div>
            )}
          </div>
          {connected && (
            <>
              <div style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
              <input
                type="text"
                placeholder="Escribe tu mensaje"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                style={{ flex: 1, padding: '8px' }}
              />
              <button onClick={sendMessage} style={{ padding: '8px 16px' }} disabled={!selectedUser || selectedUser === username}>
                Enviar
              </button>
              {/* Selector de modo de transferencia */}
              <select value={transferMode} onChange={e => setTransferMode(e.target.value)} style={{ padding: '6px', marginLeft: '8px' }}>
                <option value="FIABLE">FIABLE (seguro)</option>
                <option value="SEMI-FIABLE">SEMI-FIABLE (rápido)</option>
              </select>
              {/* Botón de subir imagen integrado */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept="image/*"
                style={{ display: 'none' }}
              />
              <button 
                onClick={() => fileInputRef.current.click()}
                style={{ padding: '8px 12px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '4px' }}
                title="Enviar imagen con fragmentación"
                disabled={!selectedUser || selectedUser === username}
              >
                📎 Imagen
              </button>
            </div>
              {/* Explicación de modos de transferencia (ahora abajo) */}
              <div style={{ margin: '10px 0', padding: '10px', background: '#f8f9fa', border: '1px solid #e0e0e0', borderRadius: '6px', fontSize: '13px' }}>
                <b>Modo de envío de imagen:</b> <br />
                <span style={{ color: '#007bff', fontWeight: 500 }}>FIABLE</span>: Entrega garantizada, cada fragmento espera confirmación (ACK), reintentos automáticos. Más lento, pero asegura que la imagen llegue completa.<br />
                <span style={{ color: '#28a745', fontWeight: 500 }}>SEMI-FIABLE</span>: Envío rápido, sin confirmaciones ni reintentos. Puede perder fragmentos si la red es inestable, pero es mucho más veloz.<br />
                <span style={{ color: '#888' }}>Recomendado: FIABLE para archivos importantes, SEMI-FIABLE para pruebas o redes estables.</span>
              </div>
            </>
          )}
          {uploadStatus && (
            <div style={{ marginTop: '10px', padding: '8px', backgroundColor: uploadStatus.includes('❌') ? '#f8d7da' : '#d4edda', border: '1px solid ' + (uploadStatus.includes('❌') ? '#f5c6cb' : '#c3e6cb'), borderRadius: '4px' }}>
              {uploadStatus}
            </div>
          )}
        </div>
        {/* Usuarios */}
        <div style={{ flex: 1 }}>
          <h3>Usuarios</h3>
          <div style={{ border: '1px solid #ccc', padding: '10px', height: '300px', backgroundColor: '#f9f9f9' }}>
            {users.map((user, index) => (
              <div key={index} style={{ padding: '4px 0', fontWeight: user === username ? 'bold' : 'normal', color: user === username ? '#007bff' : 'black', cursor: user !== username ? 'pointer' : 'default', background: user === selectedUser && user !== username ? '#e6f7ff' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                onClick={() => user !== username && handleSelectUser(user)}>
                <span>
                  {user} {user === selectedUser && user !== username ? '← destinatario' : ''}
                </span>
                {/* Badge de no leídos */}
                {user !== username && unread[user] > 0 && (
                  <span style={{ background: '#ff4136', color: 'white', borderRadius: '50%', minWidth: 18, height: 18, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, marginLeft: 8, padding: '0 6px' }}>
                    {unread[user]}
                  </span>
                )}
              </div>
            ))}
          </div>
          <div style={{ marginTop: '10px', fontSize: '13px', color: '#888' }}>
            {selectedUser && selectedUser !== username ? `Enviando a: ${selectedUser}` : 'Haz clic en un usuario para chatear'}
          </div>
        </div>
      </div>
      {!connected && (
        <p style={{ marginTop: '20px', color: '#666', fontSize: '14px' }}>
          Asegúrate de iniciar 'frontend_api' (uvicorn main:app --reload --port 8000) antes de conectar.
        </p>
      )}
    </div>
  )
}