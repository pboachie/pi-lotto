// PiAuthentication.js
import React, { useState } from 'react';
import axios from 'axios';
import '../css/PiAuthentication.css';

function PiAuthentication({ onAuthentication }) {
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  const handleAuthentication = async () => {
    setIsAuthenticating(true);
    try {
      const scopes = ['username', 'payments', 'wallet_address'];
      const Pi = window.Pi;
      const authResult = await Pi.authenticate(scopes, onIncompletePaymentFound);
      onAuthentication(await signInUser(authResult), authResult.user);
    } catch (err) {
      console.error('Authentication failed', err);
      onAuthentication(false, null);
    }
    setIsAuthenticating(false);
  };

  const signInUser = async (authResult) => {
    try {
      // Remove the access token if it exists
      if (localStorage.getItem('@pi-lotto:access_token')) {
        localStorage.removeItem('@pi-lotto:access_token');
      }

      // Fetch the access token from the server
      const response = await axios.post('http://127.0.0.1:5000/signin', { authResult });


      // Return false if status is not 200
      if (response.status !== 200) {
        return false;
      }

      // Save the access token to the local storage
      if (response.data.access_token) {
        localStorage.setItem('@pi-lotto:access_token', response.data.access_token);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Sign-in error:', error);
      return false;
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
      <div className="content">
        <h1 className="title">Pi-Lotto</h1>
        <button
          className={`auth-button ${isAuthenticating ? 'authenticating' : ''}`}
          onClick={handleAuthentication}
          disabled={isAuthenticating}
        >
          {isAuthenticating ? 'Authenticating...' : 'Login with Pi Network'}
        </button>
      </div>
    </div>
  );
}

export default PiAuthentication;