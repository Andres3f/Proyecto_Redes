import React from 'react';
import './LayerVisualization.css';

const LayerVisualization = ({ packetData, isActive }) => {
  if (!packetData) return null;

  // Determinar tipo de transferencia para mostrar información relevante
  const isImageTransfer = packetData.type === 'image_upload';
  const isMessage = packetData.type === 'message';
  const layerInfo = packetData.layerInfo || {};
  
  const layers = [
    { 
      name: 'Aplicación', 
      color: '#FF6B6B', 
      header: { 
        type: isImageTransfer ? 'Transferencia de Imagen' : 
              isMessage ? 'Mensaje de Chat' : packetData.type,
        from: `De: ${packetData.from || layerInfo.sourceUser || 'desconocido'}`,
        to: `Para: ${packetData.to || layerInfo.destUser || 'desconocido'}`,
        mode: isImageTransfer ? `Modo: ${layerInfo.reliable ? 'FIABLE' : 'SEMI-FIABLE'}` : null,
        size: packetData.size ? `Tamaño: ${(packetData.size/1024).toFixed(1)}KB` : null
      }
    },
    { 
      name: 'Sesión', 
      color: '#4ECDC4', 
      header: { 
        sessionId: `ID Sesión: ${layerInfo.sessionId || 'N/A'}`,
        sequence: isImageTransfer 
          ? `Fragmentos: ${layerInfo.sequence || 1}`
          : `Secuencia: ${layerInfo.sequence || 1}`,
        progress: packetData.progress ? `Progreso: ${packetData.progress}%` : null
      } 
    },
    { 
      name: 'Transporte', 
      color: '#45B7D1', 
      header: { 
        reliable: `Control: ${layerInfo.reliable ? 'ACK Requerido' : 'Sin ACK'}`,
        fragmentId: `ID Fragmento: ${layerInfo.fragmentId || 'N/A'}`,
        status: isImageTransfer 
          ? (layerInfo.reliable 
             ? layerInfo.ackReceived 
               ? 'ACK Recibido'
               : 'Esperando ACK...' 
             : 'Enviando...')
          : null,
        retries: layerInfo.retries ? `Reintentos: ${layerInfo.retries}` : null
      } 
    },
    { 
      name: 'Red', 
      color: '#96CEB4', 
      header: { 
        sourceIp: `Origen: ${layerInfo.sourceIp || 'desconocido'}`,
        destIp: `Destino: ${layerInfo.destIp || 'desconocido'}`,
        protocol: isImageTransfer ? 'Protocolo: TCP/UDP' : 'Protocolo: TCP'
      } 
    }
  ];

  return (
    <div className="layer-visualization" style={{ 
      opacity: isActive ? 1 : 0.3, 
      transition: 'opacity 0.3s',
      animation: isActive ? 'pulse 2s infinite' : 'none',
      width: '100%',
      maxWidth: '100%',
      overflowX: 'hidden'
    }}>
      <h4 style={{ 
        marginBottom: '15px',
        color: '#333',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        width: '100%'
      }}>
          Simulación de Capas
        {isActive && packetData.type === 'image_upload' && 
          <span style={{ fontSize: '0.8em', color: '#666' }}>
            (Transferencia en progreso)
          </span>
        }
      </h4>
      <div className="layers-container" style={{
        width: '100%',
        maxWidth: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}>
        {layers.map((layer, index) => (
          <div key={layer.name} className="layer" style={{ 
            backgroundColor: layer.color,
            opacity: 0.95
          }}>
            <div className="layer-name" style={{ 
              fontWeight: 'bold', 
              marginBottom: '8px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>{layer.name}</span>
              {isActive && <span style={{ fontSize: '0.8em', opacity: 0.7 }}></span>}
            </div>
            <div className="layer-headers">
              {Object.entries(layer.header).map(([key, value]) => (
                value && (
                  <div key={key}>
                    {value}
                  </div>
                )
              ))}
            </div>
          </div>
        ))}
      </div>
      <style>
        {`
          @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.02); }
            100% { transform: scale(1); }
          }
        `}
      </style>
    </div>
  );
};

export default LayerVisualization;