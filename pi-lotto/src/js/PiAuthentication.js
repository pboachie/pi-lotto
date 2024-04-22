import React, { useState } from 'react';
import axios from 'axios';

import '../css/PiAuthentication.css';


function PiAuthentication({ onAuthentication }) {
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  const handleAuthentication = async () => {
    setIsAuthenticating(true);
    try {
      const scopes = ['username', 'payments'];
      const Pi = window.Pi;
      const authResult = await Pi.authenticate(scopes, onIncompletePaymentFound);
      await signInUser(authResult);
      onAuthentication(true, authResult.user);
    } catch (err) {
      console.error('Authentication failed', err);
      onAuthentication(false, null);
    }
    setIsAuthenticating(false);
  };

  const signInUser = async (authResult) => {
    try {

      if (localStorage.getItem('@pi-lotto:access_token')) {
        localStorage.removeItem('@pi-lotto:access_token');
      }

      const response = await axios.post('http://127.0.0.1:5000/signin', { authResult });

      if(response.data.access_token) {
        localStorage.setItem('@pi-lotto:access_token', response.data.access_token);
      }
    } catch (error) {
      console.error('Sign-in error:', error);
    }
  };

  const onIncompletePaymentFound = async (payment) => {
    console.log('Incomplete payment found:', payment);
    try {
      const response = await axios.post('/incomplete', { payment });
      console.log(response.data);
    } catch (error) {
      console.error('Incomplete payment error:', error);
    }
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