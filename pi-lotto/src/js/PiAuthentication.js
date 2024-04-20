import React, { useState } from 'react';
import '../css/PiAuthentication.css';

function PiAuthentication({ onAuthentication }) {
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  const handleAuthentication = async () => {
    setIsAuthenticating(true);
    try {
      const scopes = ['username', 'payments'];
      const Pi = window.Pi;
      const authResult = await Pi.authenticate(scopes, onIncompletePaymentFound);
      onAuthentication(true, authResult.user);
    } catch (err) {
      console.error('Authentication failed', err);
      onAuthentication(false, null);
    }
    setIsAuthenticating(false);
  };

  const onIncompletePaymentFound = (payment) => {
    console.log('Incomplete payment found:', payment);
    // Handle incomplete payment if needed
  };

  return (
    <div className="pi-authentication">
      <h2>Authenticate with Pi Network</h2>
      <button
        className={`auth-button ${isAuthenticating ? 'authenticating' : ''}`}
        onClick={handleAuthentication}
        disabled={isAuthenticating}
      >
        {isAuthenticating ? 'Authenticating...' : 'Authenticate'}
      </button>
    </div>
  );
}

export default PiAuthentication;