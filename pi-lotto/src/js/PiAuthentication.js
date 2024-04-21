import React, { useState } from 'react';
import '../css/PiAuthentication.css';
import axios from 'axios';

function PiAuthentication({ onAuthentication }) {
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  const handleAuthentication = async () => {
    setIsAuthenticating(true);
    try {
      const scopes = ['username', 'payments'];
      const Pi = window.Pi;
      const authResult = await Pi.authenticate(scopes, onIncompletePaymentFound);

       // Send the user's ID to the backend for token generation
       const response = await axios.post('http://127.0.0.1:5000/login', { uid: authResult.user.uid });
       const { access_token } = response.data;

      // Store the access token in local storage or state management solution (Improve to use a secure storage solution)
      localStorage.setItem('access_token', access_token);

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