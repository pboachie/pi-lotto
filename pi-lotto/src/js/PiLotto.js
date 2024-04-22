import React, { useEffect, useState } from 'react';
import Lotto from '../js/Lotto';
import PiAuthentication from '../js/PiAuthentication';
import '../css/PiLotto.css';
import axios from 'axios';


function PiLotto() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [lottoPool, setLottoPool] = useState(0);

  useEffect(() => {
    const Pi = window.Pi;
    Pi.init({ version: "2.0", sandbox: process.env.NODE_ENV !== 'production' });
  }, []);

  useEffect(() => {
    if (isAuthenticated && user) {
      fetchLottoPool();
    }
  }, [isAuthenticated, user]);

  const handleAuthentication = (authenticated, userInfo) => {
    setIsAuthenticated(authenticated);
    setUser(userInfo);
  };

  const fetchLottoPool = async () => {
    try {
      const response = await axios.get('http://127.0.0.1:5000/api/lotto-pool', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('@pi-lotto:access_token')}`,
        },
      });

      // check if balance else set to 0 and display error
      if (!response.data.balance) {
        setLottoPool(0);
        // Alert error message from server
        alert(response.data.error);
        return;
      }

      const lottoPool = response.data.balance;
      setLottoPool(lottoPool);
    } catch (error) {
      // Show the error
      alert('Server currently under maintenance. Please try again later.');
    }
  };

  return (
    <div className="pi-lotto">
      <header>
        <h1>Win {process.env.NODE_ENV !== 'production' ? 'Test-' : ''}π Today!</h1>
        {isAuthenticated && (
          <div className="lotto-pool">

            Current Lotto Pool: {lottoPool} {process.env.NODE_ENV !== 'production' ? 'Test-' : ''}π
          </div>
        )}
      </header>
      <main>
        {!isAuthenticated ? (
          <PiAuthentication onAuthentication={handleAuthentication} />
        ) : (
          <div>
            <h2>Welcome, {user.username}!</h2>
            <Lotto />
          </div>
        )}
      </main>
    </div>
  );
}

export default PiLotto;