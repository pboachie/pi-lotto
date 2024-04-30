// PiLotto.js
import React, { useEffect, useState } from 'react';
import Lotto from '../js/Lotto';
import PiAuthentication from '../js/PiAuthentication';
import SideMenu from '../js/SideMenu';
import '../css/PiLotto.css';
import axios from 'axios';
import { FaBars } from 'react-icons/fa';

function PiLotto() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  // const [lottoPool, setLottoPool] = useState(0);
  const [userBalance, setUserBalance] = useState(0);
  const [selectedGame, setSelectedGame] = useState(null);
  const [isSideMenuOpen, setIsSideMenuOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const Pi = window.Pi;
    Pi.init({ version: "2.0", sandbox: process.env.NODE_ENV !== 'production' });
  }, []);

  useEffect(() => {
    if (isAuthenticated && user) {
      // fetchLottoPool();
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

  // const fetchLottoPool = async () => {
  //   try {
  //     const response = await axios.get('http://127.0.0.1:5000/api/lotto-pool', {
  //       headers: {
  //         Authorization: `Bearer ${localStorage.getItem('@pi-lotto:access_token')}`,
  //       },
  //     });

  //     if (!response.data.balance) {
  //       setLottoPool(0);
  //       alert(response.data.error);
  //       return;
  //     }

  //     const lottoPool = response.data.balance;
  //     setLottoPool(lottoPool);
  //   } catch (error) {
  //     alert('Server currently under maintenance. Please try again later.');
  //   }
  // };

  const fetchUserBalance = async () => {
    try {
      const response = await axios.get('http://localhost:5000/api/user-balance', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('@pi-lotto:access_token')}`,
        },
      });

      // if response is not 200, return false
      const status = response.status === 200;

      if (!status) {
        setUserBalance(0);
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
    }, 2000); // Simulating loading delay
  };

  const toggleSideMenu = () => {
    setIsSideMenuOpen(!isSideMenuOpen);
  };

  const renderMainContent = () => {
    if (!isAuthenticated) {
      return <PiAuthentication onAuthentication={handleAuthentication} />;
    }

    if (isLoading) {
      return <div className="loading">Loading...</div>;
    }

    if (selectedGame === 'lotto') {
      return <Lotto />;
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
            <span>Welcome, {user.username}</span>
            <span>Balance: {userBalance} Test-π</span>
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