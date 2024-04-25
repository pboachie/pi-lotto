// SideMenu.js
import React from 'react';
import '../css/SideMenu.css';
import { FaTimes } from 'react-icons/fa';

function SideMenu({ isOpen, onGameClick, onClose }) {
  const handleGameClick = (game) => {
    onGameClick(game);
    onClose();
  };

  return (
    <>
      <div className={`side-menu ${isOpen ? 'open' : ''}`}>
        <button className="close-btn" onClick={onClose}>
          <FaTimes />
        </button>
        <h3>Available Games</h3>
        <ul>
          <li>
            <button onClick={() => handleGameClick('lotto')}>Pi Lotto</button>
          </li>
          {/* Add more games here */}
        </ul>
      </div>
      {isOpen && <div className="side-menu-backdrop" onClick={onClose}></div>}
    </>
  );
}

export default SideMenu;