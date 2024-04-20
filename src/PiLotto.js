import React, { useEffect, useState } from 'react';
import Lotto from './Lotto';
import PiAuthentication from './PiAuthentication';
import './PiLotto.css';

function PiLotto() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const Pi = window.Pi;
    Pi.init({ version: "2.0", sandbox: process.env.NODE_ENV !== 'production' });
  }, []);

  const handleAuthentication = (authenticated, userInfo) => {
    setIsAuthenticated(authenticated);
    setUser(userInfo);
  };

  return (
    <div className="pi-lotto">
      <header>
        <h1>Pi-Lotto</h1>
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