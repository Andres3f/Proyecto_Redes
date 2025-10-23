import React from 'react';
import './LayerVisualization.css';

const LayerVisualization = ({ packetData, isActive }) => {
  if (!packetData) return null;

  const layers = [
    { name: 'Aplicación', color: '#FF6B6B', header: { type: packetData.type, from: packetData.from, to: packetData.to } },
    { name: 'Sesión', color: '#4ECDC4', header: { sessionId: packetData.sessionId, sequence: packetData.sequence } },
    { name: 'Transporte', color: '#45B7D1', header: { reliable: packetData.reliable, fragmentId: packetData.fragmentId } },
    { name: 'Red', color: '#96CEB4', header: { sourceIp: packetData.sourceIp, destIp: packetData.destIp } }
  ];

  return (
    <div className="layer-visualization" style={{ opacity: isActive ? 1 : 0.3, transition: 'opacity 0.3s' }}>
      <h4>Simulación de Capas</h4>
      <div className="layers-container">
        {layers.map((layer, index) => (
          <div key={layer.name} className="layer" style={{ 
            backgroundColor: layer.color,
            padding: '10px',
            margin: '5px',
            borderRadius: '5px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
          }}>
            <div className="layer-name" style={{ fontWeight: 'bold', marginBottom: '5px' }}>
              {layer.name}
            </div>
            <div className="layer-headers" style={{ 
              fontSize: '0.8em',
              backgroundColor: 'rgba(255,255,255,0.9)',
              padding: '5px',
              borderRadius: '3px'
            }}>
              {Object.entries(layer.header).map(([key, value]) => (
                value && <div key={key}>{key}: {value}</div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LayerVisualization;