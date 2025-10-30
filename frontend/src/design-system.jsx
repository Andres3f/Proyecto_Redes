import React from 'react';
import './design-system.css';

export const Button = ({ children, variant = 'primary', ...props }) => {
  return (
    <button 
      className={`ds-btn ds-btn-${variant}`}
      {...props}
    >
      <span className="ds-btn-content">{children}</span>
      <span className="ds-btn-ripple"></span>
    </button>
  );
};

export const Card = ({ children, elevated }) => (
  <div className={`ds-card ${elevated ? 'ds-card-elevated' : ''}`}>
    <div className="ds-card-inner">
      {children}
    </div>
  </div>
);

export const ProgressBar = ({ value, max = 100 }) => (
  <div className="ds-progress-bar">
    <div 
      className="ds-progress-fill" 
      style={{ width: `${(value/max)*100}%` }}
    ></div>
  </div>
);
