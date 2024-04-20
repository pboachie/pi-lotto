import React, { useEffect, useState } from 'react';
import Lotto from '../js/Lotto';
import PiAuthentication from '../js/PiAuthentication';
import '../css/PiLotto.css';
import config from '../config.json';
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
      const appWalletSeed = config.APP_WALLET_SEED;
      const appWalletAddress = config.APP_WALLET_ADDRESS;
      const apiKey = config.APP_API_KEY;

      const response = await axios.get(`https://api.minepi.com/v2/wallets/${appWalletAddress}`, {
        headers: {
          'Authorization': `Key ${apiKey}`,
          'Content-Type': 'application/json'
        },
        params: {
          seed: appWalletSeed
        }
      });

      const walletInfo = response.data;
      setLottoPool(walletInfo.balance);
    } catch (error) {
      console.error('Error fetching lotto pool amount:', error);
    }
  };

  return (
    <div className="pi-lotto">
      <header>
        <h1>Pi-Lotto</h1>
        {isAuthenticated && (
          <div className="lotto-pool">
            Current Lotto Pool: {lottoPool} Pi
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