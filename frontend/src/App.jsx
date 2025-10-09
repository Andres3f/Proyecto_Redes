import React, { useEffect, useRef, useState } from 'react'

export default function App() {
  const [username, setUsername] = useState('')
  const [connected, setConnected] = useState(false)
  const [users, setUsers] = useState([])
  const [messages, setMessages] = useState([])
  const [to, setTo] = useState('')
  const [text, setText] = useState('')
  const wsRef = useRef(null)

  const connect = () => {
    if (!username) return
    const ws = new WebSocket('ws://localhost:8000/ws')
    wsRef.current = ws
    ws.addEventListener('open', () => {
      ws.send(JSON.stringify({ type: 'register', username }))
      setConnected(true)
    })
    ws.addEventListener('message', (ev) => {
      try {
        const pkt = JSON.parse(ev.data)
        if (pkt.type === 'message') {
          setMessages((m) => [...m, { from: pkt.from, msg: pkt.msg }])
        } else if (pkt.type === 'list') {
          setUsers(pkt.users.filter((u) => u !== username))
        }
      } catch (e) {
        // ignorar
      }
    })
    ws.addEventListener('close', () => setConnected(false))
  }

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setConnected(false)
  }

  const requestList = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'list' }))
    }
  }

  const sendMessage = () => {
    if (!to || !text) return
    const pkt = { type: 'message', to, msg: text }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(pkt))
      setMessages((m) => [...m, { from: username, msg: text }])
      setText('')
    }
  }

  useEffect(() => {
    const t = setInterval(() => {
      if (connected) requestList()
    }, 3000)
    return () => clearInterval(t)
  }, [connected])

  return (
    <div className="container">
      <h1>Chat — Proyecto Redes</h1>

      {!connected ? (
        <div>
          <input placeholder="Tu nombre" value={username} onChange={(e) => setUsername(e.target.value)} />
          <button onClick={connect} style={{ marginLeft: 8 }}>Conectar</button>
        </div>
      ) : (
        <div>
          <div style={{ marginBottom: 8 }}>Conectado como <strong>{username}</strong>
            <button onClick={disconnect} style={{ marginLeft: 12 }}>Desconectar</button>
          </div>

          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ flex: 1 }}>
              <h3>Mensajes</h3>
              <div style={{ height: 300, overflow: 'auto', border: '1px solid #e5e7eb', padding: 8 }}>
                {messages.map((m, i) => (
                  <div key={i}><strong>{m.from}:</strong> {m.msg}</div>
                ))}
              </div>
            </div>

            <div style={{ width: 240 }}>
              <h3>Usuarios</h3>
              <div style={{ border: '1px solid #e5e7eb', padding: 8, minHeight: 100 }}>
                {users.length === 0 ? <div style={{ color: '#6b7280' }}>No hay usuarios conectados</div> : users.map((u) => (
                  <div key={u} style={{ padding: 6, cursor: 'pointer' }} onClick={() => setTo(u)}>{u}</div>
                ))}
              </div>

              <div style={{ marginTop: 12 }}>
                <div>Enviar a: <strong>{to || '(selecciona usuario)'}</strong></div>
                <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Escribe tu mensaje" style={{ width: '100%', height: 80 }} />
                <button onClick={sendMessage} style={{ marginTop: 8 }}>Enviar</button>
              </div>
            </div>
          </div>
        </div>
      )}

      <p className="note">Asegúrate de iniciar `frontend_api` (uvicorn main:app --reload --port 8000) antes de conectar.</p>
    </div>
  )
}
