// PiLotto.js
import React, { useEffect, useState, useRef } from 'react';
import Lotto from '../js/Lotto';
import PiAuthentication from '../js/PiAuthentication';
import SideMenu from '../js/SideMenu';
import PiDeposit from '../js/PiDeposit';

import '../css/PiLotto.css';
import axios from 'axios';
import { FaBars, FaUser } from 'react-icons/fa';

function PiLotto() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [userBalance, setUserBalance] = useState(parseFloat(0.0));
  const [selectedGame, setSelectedGame] = useState(null);
  const [isSideMenuOpen, setIsSideMenuOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isDepositVisible, setIsDepositVisible] = useState(false);
  const userIconRef = useRef(null);

  useEffect(() => {
    const Pi = window.Pi;
    Pi.init({ version: "2.0", sandbox: process.env.NODE_ENV !== 'production' });
  }, []);

  useEffect(() => {
    if (isAuthenticated && user) {
      fetchUserBalance();
    }
  }, [isAuthenticated, user]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => {
      clearInterval(timer);
    };
  }, []);

  const handleAuthentication = (authenticated, userInfo) => {
    setIsAuthenticated(authenticated);
    setUser(userInfo);
  };

  const fetchUserBalance = async () => {
    try {
      const response = await axios.get('http://localhost:5000/api/user-balance', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('@pi-lotto:access_token')}`,
        },
      });

      const status = response.status === 200;

      if (!status) {
        setUserBalance(parseFloat(0.0));
        alert(response.data.error);
        return;
      }

      setUserBalance(parseFloat(response.data.balance));
    } catch (error) {
      alert('Server currently under maintenance. Please try again later.');
    }
  };

  const handleGameClick = (game) => {
    setSelectedGame(game);
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
    }, 2000);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userIconRef.current && !userIconRef.current.contains(event.target)) {
        setIsUserMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const toggleSideMenu = () => {
    setIsSideMenuOpen(!isSideMenuOpen);
  };

  const toggleUserMenu = () => {
    setIsUserMenuOpen(!isUserMenuOpen);
  };

  const handleDeposit = () => {
    setIsDepositVisible(true);
  };

  const handleWithdraw = () => {
    // Implement withdraw functionality
    console.log('Withdraw clicked');
  };

  const handleLogout = () => {
    // Clear the access token from the local storage
    localStorage.removeItem('@pi-lotto:access_token');

    // Reset the user state
    setIsAuthenticated(false);
    setUser(null);
    setUserBalance(parseFloat(0.0));

    // Close the user menu
    setIsUserMenuOpen(false);

    // Close the side menu
    setIsSideMenuOpen(false);

    // Reset the selected game
    setSelectedGame(null);

    // reset the deposit visibility
    setIsDepositVisible(false);

    alert('You have been logged out.');
  };

  const renderMainContent = () => {
    if (!isAuthenticated) {
      return <PiAuthentication
        onAuthentication={handleAuthentication}
        isAuthenticated={isAuthenticated}
        onBalanceUpdate={fetchUserBalance}
      />;
    }

    if (isLoading) {
      return <div className="loading">Loading...</div>;
    }

    if (selectedGame === 'lotto') {
      return <Lotto />;
    }

    if (isDepositVisible) {
      return <PiDeposit onClose={() => setIsDepositVisible(false)} isAuthenticated={isAuthenticated} userBalance={userBalance} setUserBalance={setUserBalance} />


    }

    return (
      <div className="home-page">
        <h2>Current Local Time:</h2>
        <p className="current-time">{currentTime.toLocaleString()}</p>
      </div>
    );
  };

  return (
    <div className="pi-lotto">
      <header className="top-bar">
        <button className="menu-btn" onClick={toggleSideMenu}>
          <FaBars />
        </button>
        <h1>Pi-Lotto</h1>
        {isAuthenticated && (
        <div className="user-info">
          <div className="user-details">
            <span>Welcome, {user.username}</span>
            <span>Balance: {userBalance} {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</span>
          </div>
          <div className={`user-icon ${isUserMenuOpen ? 'active' : ''}`} onClick={toggleUserMenu} ref={userIconRef}>
            <FaUser />
            {isUserMenuOpen && (
              <div className="user-menu">
                <button onClick={handleDeposit}>Deposit</button>
                <button onClick={handleWithdraw}>Withdraw</button>
                <button onClick={handleLogout}>Logout</button>
              </div>
            )}
          </div>
        </div>
        )}
      </header>
      {isAuthenticated && (
        <SideMenu isOpen={isSideMenuOpen} onGameClick={handleGameClick} onClose={toggleSideMenu} />
      )}
      <div className="main-content">{renderMainContent()}</div>
    </div>
  );
}

export default PiLotto;