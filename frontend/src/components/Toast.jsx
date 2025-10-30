import React, { useState, useEffect, createContext } from 'react';
import './Toast.css';

export const ToastContext = createContext();

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const addToast = (message, type = 'info', duration = 5000) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    
    if (duration > 0) {
      setTimeout(() => removeToast(id), duration);
    }
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="ds-toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`ds-toast ds-toast-${toast.type}`}>
            <div className="ds-toast-message">{toast.message}</div>
            <button 
              onClick={() => removeToast(toast.id)}
              className="ds-toast-close"
              aria-label="Cerrar notificación"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  return React.useContext(ToastContext);
};
