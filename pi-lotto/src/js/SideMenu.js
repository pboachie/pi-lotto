// SideMenu.js
import React from 'react';
import '../css/SideMenu.css';
import { FaTimes, FaHome } from 'react-icons/fa';

function SideMenu({ isOpen, onGameClick, onClose, onCloseComponents, gameTypes}) {
  const handleGameClick = (game) => {
    onGameClick(game);
    onClose();
  };

  const handleHomeClick = () => {
    // Clear all components like deposit, lotto, etc dynamically

    onGameClick(null);
    onClose();
    onCloseComponents();
  };

  return (
    <>
      <div className={`side-menu ${isOpen ? 'open' : ''}`}>
        <button className="close-btn" onClick={onClose}>
          <FaTimes />
        </button>
        <h3>Menu</h3>
        <ul>
          <li>
            <button onClick={handleHomeClick}>
              <FaHome /> Home
            </button>
          </li>
          {gameTypes.map((gameType) => (
            <li key={gameType.id}>
              {/* Remove special characters and convert to lowercase */}
              <button onClick={() => handleGameClick(gameType.name.replace(/[^a-zA-Z0-9]/g, '').toLowerCase())} className="game-btn">
                {gameType.name}
              </button>
            </li>
          ))}
        </ul>
      </div>
      {isOpen && <div className="side-menu-backdrop" onClick={onClose}></div>}
    </>
  );
}

export default SideMenu;