import React, { useState, useRef, useEffect } from 'react'
import './styles_new.css'
import LayerVisualization from './components/LayerVisualization'

// Icono para el modo oscuro usando un SVG personalizado
const ModeNightIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
  </svg>
)

export default function App() {
  // Estados para autenticación y conexión
  const [username, setUsername] = useState('')
  const [connected, setConnected] = useState(false)
  const [socket, setSocket] = useState(null)
  const [userIP, setUserIP] = useState('')
  const [darkMode, setDarkMode] = useState(() => {
    const savedTheme = localStorage.getItem('theme')
    return savedTheme === 'dark'
  })
  
  // Estados para el chat
  const [chatHistory, setChatHistory] = useState({}) // { usuario: [ {from, to, content} ] }
  const [unread, setUnread] = useState({}) // { usuario: cantidad }
  const [users, setUsers] = useState([])
  const [userIPs, setUserIPs] = useState({})  // Mapeo de usuarios a IPs
  const [newMessage, setNewMessage] = useState('')
  const [selectedUser, setSelectedUser] = useState('')
  const messagesEndRef = useRef(null) // Para auto-scroll

  // Estados para funcionalidad de imágenes y modo de envío
  const [uploadStatus, setUploadStatus] = useState('')
  const [transferStats, setTransferStats] = useState(null)
  const [transferMode, setTransferMode] = useState('FIABLE')
  const fileInputRef = useRef(null)
  const [simulationData, setSimulationData] = useState(null)
  const [isSimulating, setIsSimulating] = useState(false)
  const [ngrokUrl, setNgrokUrl] = useState('')

  // Efecto para manejar el cambio de tema
  useEffect(() => {
    if (darkMode) {
      document.documentElement.setAttribute('data-theme', 'dark')
      document.body.setAttribute('data-theme', 'dark')
    } else {
      document.documentElement.setAttribute('data-theme', 'light')
      document.body.setAttribute('data-theme', 'light')
    }
    localStorage.setItem('theme', darkMode ? 'dark' : 'light')
    console.log('Tema cambiado a:', darkMode ? 'dark' : 'light') // Para debugging
  }, [darkMode])

  // Función para alternar el modo oscuro
  const toggleDarkMode = () => {
    setDarkMode(prev => !prev)
  }

  // Obtener URL de ngrok al cargar
  useEffect(() => {
    const getNgrokUrl = async () => {
      try {
        const response = await fetch('http://localhost:4040/api/tunnels')
        const data = await response.json()
        const url = data.tunnels[0]?.public_url
        if (url) {
          setNgrokUrl(url)
          console.log('Ngrok URL:', url)
        }
      } catch (error) {
        console.warn('No se pudo obtener la URL de ngrok:', error)
      }
    }
    getNgrokUrl()
  }, [])
  
  // Conectar WebSocket
  const connectWebSocket = () => {
    if (username.trim()) {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      // Si tenemos URL de ngrok, usarla; si no, usar la URL relativa
      const wsUrl = ngrokUrl 
        ? `${ngrokUrl.replace('http', 'ws')}/api/ws`
        : `${wsProtocol}//${window.location.host}/api/ws`
      const ws = new WebSocket(wsUrl)
      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'register', username }))
        ws.send(JSON.stringify({ type: 'list' }))
        setConnected(true)
        setSocket(ws)
      }
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'ip_assigned') {
          setUserIP(data.ip)
          // Actualizar el IP del usuario actual en el mapeo
          setUserIPs(prev => ({
            ...prev,
            [username]: data.ip
          }))
        } else if (data.type === 'message') {
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

          // Actualizar simulación si el mensaje tiene información de capas
          if (data.layerInfo) {
            setIsSimulating(true);
            setSimulationData({
              type: 'message',
              from: from,
              to: to,
              msg: data.msg || data.content || '',
              layerInfo: data.layerInfo
            });
            
            // Desactivar simulación después de 2 segundos
            setTimeout(() => {
              setIsSimulating(false);
            }, 2000);
          }
        } else if (data.type === 'list' || data.type === 'user_list') {
          const userList = data.users || [];
          setUsers(userList)
          // Cuando obtenemos la lista de usuarios, guardar sus IPs
          userList.forEach(user => {
            if (data.userIPs && data.userIPs[user]) {
              setUserIPs(prev => ({
                ...prev,
                [user]: data.userIPs[user]
              }))
            }
          })
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
      // Iniciar simulación
      setIsSimulating(true)
      const initialSimData = {
        type: 'message',
        from: username,
        to: selectedUser,
        msg: newMessage,
        layerInfo: {
          sessionId: Math.random().toString(36).substr(2, 8),
          sequence: 1,
          reliable: true,
          fragmentId: 'MSG-1',
          sourceIp: userIPs[username] || userIP,
          destIp: userIPs[selectedUser] || 'desconocido',
          sourceUser: username,
          destUser: selectedUser
        }
      }
      console.log('Simulation data:', initialSimData);
      setSimulationData(initialSimData)

      // Enviar por WebSocket
      socket.send(JSON.stringify({
        type: 'message',
        to: selectedUser,
        msg: newMessage
      }))
      
      // Terminar simulación después de 2 segundos
      setTimeout(() => {
        setIsSimulating(false)
      }, 2000)

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
    
    // Iniciar simulación
    setIsSimulating(true)
    const sessionId = Math.random().toString(36).substr(2, 8);
    const fileSize = file.size;
    const estimatedChunks = Math.ceil(fileSize / 4096);
    
    const simulationPacket = {
      type: 'image_upload',
      from: username,
      to: selectedUser,
      sessionId: sessionId,
      sequence: `0/${estimatedChunks}`,
      reliable: transferMode === 'FIABLE',
      fragmentId: `IMG-${Date.now()}`,
      sourceIp: userIP,
      destIp: userIPs[selectedUser] || '172.20.0.3',
      size: fileSize,
      progress: 0,
      retries: 0,
      ackReceived: false
    }
    setSimulationData(simulationPacket)

    try {
      setUploadStatus('Subiendo imagen...')
      // Usar URL de ngrok si está disponible, si no usar ruta relativa
      const baseUrl = ngrokUrl || ''
      const response = await fetch(`${baseUrl}/api/upload-image`, {
        method: 'POST',
        body: formData
      })
      const result = await response.json()
      if (result.status === 'sent') {
        setUploadStatus(`✅ Imagen enviada: ${result.filename}`)
        setTransferStats(result.stats)
        
        // Actualizar simulación con datos reales
        if (result.stats) {
          const totalChunks = result.stats.total_chunks || 1;
          const sentChunks = result.stats.sent_chunks || 1;
          const progress = Math.round((sentChunks / totalChunks) * 100);
          
          setSimulationData(prev => ({
            ...prev,
            reliable: transferMode === 'FIABLE',
            fragmentId: `IMG-${result.stats.chunks || 1}`,
            sequence: `${sentChunks}/${totalChunks}`,
            progress: progress,
            retries: result.stats.retries || 0,
            ackReceived: result.stats.acks_received > 0,
            size: result.stats.total_bytes || file.size
          }))
        }
        
        // Enviar mensaje de imagen al usuario seleccionado
        if (socket) {
          // Suponiendo que el backend guarda la imagen en /received/<filename>
          if (!result.filename) {
            setUploadStatus('❌ Error: No se recibió el nombre seguro del archivo.');
            setTimeout(() => setUploadStatus(''), 5000);
            return;
          }
          // Construir la URL de la imagen usando el mismo host de la API
          const baseUrl = ngrokUrl || ''
          const imageUrl = `${baseUrl}/api/received/${result.filename}`
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
        // Mantener la simulación por 2 segundos más y luego terminar
        setTimeout(() => {
          setIsSimulating(false)
          setUploadStatus('')
        }, 3000)
      } else {
        setUploadStatus(`❌ Error: ${result.error || 'No se pudo enviar la imagen.'}`)
        setTimeout(() => setUploadStatus(''), 5000)
      }
    } catch (error) {
      setUploadStatus(`❌ Error: ${error.message}`)
      setTimeout(() => setUploadStatus(''), 5000)
      // Terminar simulación en caso de error
      setIsSimulating(false)
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
    <div className="app-container">
      <div className="header">
        <h1>Chat — Proyecto Redes</h1>
        <button 
          onClick={toggleDarkMode} 
          className="theme-toggle"
          aria-label="Alternar modo oscuro"
          title={darkMode ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
        >
          <ModeNightIcon />
        </button>
      </div>
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
          <span>
            Conectado como <strong>{username}</strong>
            {userIP && <span style={{ marginLeft: '10px', color: '#666' }}>(IP: {userIP})</span>}
          </span>
          <button 
            onClick={disconnectWebSocket} 
            className="action-button"
          >
            Desconectar
          </button>
        </div>
      )}
      <div style={{ display: 'flex', gap: '20px' }}>
        {/* Mensajes */}
        <div style={{ flex: 2 }}>
          <h3>Mensajes</h3>
          <div className="messages">
            {/* Mostrar solo la conversación con el usuario seleccionado */}
            {selectedUser && chatHistory[selectedUser] && chatHistory[selectedUser].length > 0 ? (
              chatHistory[selectedUser].map((msg, index) => (
                <div key={index} className={`message ${msg.from === username ? 'sent' : 'received'}`}>
                  <span className="message-sender">
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
              <div className="transfer-mode-info">
                <b>Modo de envío de imagen:</b> <br />
                <span className="mode-fiable">FIABLE</span>: Entrega garantizada, cada fragmento espera confirmación (ACK), reintentos automáticos. Más lento, pero asegura que la imagen llegue completa.<br />
                <span className="mode-semi-fiable">SEMI-FIABLE</span>: Envío rápido, sin confirmaciones ni reintentos. Puede perder fragmentos si la red es inestable, pero es mucho más veloz.<br />
                <span className="mode-recommendation">Recomendado: FIABLE para archivos importantes, SEMI-FIABLE para pruebas o redes estables.</span>
              </div>
            </>
          )}
          {uploadStatus && (
            <div className={`upload-status ${uploadStatus.includes('❌') ? 'error' : 'success'}`}>
              {uploadStatus}
            </div>
          )}
        </div>
        {/* Simulación de Capas */}
        <div style={{ flex: 1.5 }}>
          <h3>Visualización de Capas</h3>
          <div className="layer-visualization-panel">
            <LayerVisualization 
              packetData={simulationData}
              isActive={isSimulating}
            />
          </div>
        </div>
        {/* Usuarios */}
        <div style={{ flex: 1 }}>
          <h3>Usuarios</h3>
          <div className="users-container">
            {users.map((user, index) => (
              <div 
                key={index} 
                className={`user-list-item ${user === username ? 'current-user' : ''} ${user === selectedUser && user !== username ? 'selected' : ''}`}
                onClick={() => user !== username && handleSelectUser(user)}
              >
                <span>
                  {user} {user === selectedUser && user !== username ? '← destinatario' : ''}
                </span>
                {/* Badge de no leídos */}
                {user !== username && unread[user] > 0 && (
                  <span className="unread-badge">
                    {unread[user]}
                  </span>
                )}
              </div>
            ))}
          </div>
          <div className="user-status-message">
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