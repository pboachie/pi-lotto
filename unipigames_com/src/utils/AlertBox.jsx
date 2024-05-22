import React from 'react';
import './AlertBox.css'; // Ensure this CSS file is imported

const AlertBox = ({ title, body, onClose }) => {
  return (
    <div className="alert-container">
      <div className="alert-box">
        <div className="alert-header">
          <h2 className="alert-title">{title}</h2>
        </div>
        <div className="alert-body">
          <p className="alert-message">{body}</p>
        </div>
        <div className="alert-footer">
          <button onClick={onClose} className="alert-button">
            Ok
          </button>
        </div>
      </div>
    </div>
  );
};

export default AlertBox;
