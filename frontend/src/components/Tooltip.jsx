import React, { useState, useRef } from 'react';
import './Tooltip.css';

export const Tooltip = ({ 
  content, 
  children, 
  position = 'top',
  delay = 300
}) => {
  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState({});
  const triggerRef = useRef(null);
  let timeout;

  const showTooltip = () => {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setCoords({
        left: rect.left + rect.width / 2,
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom
      });
    }
    timeout = setTimeout(() => setVisible(true), delay);
  };

  const hideTooltip = () => {
    clearTimeout(timeout);
    setVisible(false);
  };

  return (
    <div className="ds-tooltip-wrapper">
      <div
        ref={triggerRef}
        className="ds-tooltip-trigger"
        onMouseEnter={showTooltip}
        onMouseLeave={hideTooltip}
      >
        {children}
      </div>
      {visible && (
        <div 
          className={`ds-tooltip ds-tooltip-${position}`}
          style={{
            left: `${coords.left}px`,
            top: position.includes('bottom') ? `${coords.bottom + 8}px` : 'auto',
            bottom: position.includes('top') ? `calc(100vh - ${coords.top - 8}px)` : 'auto'
          }}
        >
          {content}
          <div className="ds-tooltip-arrow"></div>
        </div>
      )}
    </div>
  );
};
