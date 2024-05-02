// PiAuthentication.js
import React from 'react';
import axios from 'axios';
import '../css/PiAuthentication.css';

function PiAuthentication({ onAuthentication, isAuthenticated, onBalanceUpdate }) {
  const handleAuthentication = async () => {
    try {
      const scopes = ['username', 'payments', 'wallet_address'];
      const Pi = window.Pi;
      const authResult = await Pi.authenticate(scopes, onIncompletePaymentFound);
      onAuthentication(await signInUser(authResult), authResult.user);
    } catch (err) {
      console.error('Authentication failed', err);
      onAuthentication(false, null);
    }
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
    try {
      // Get paymentId
      const paymentId = payment.identifier;
      const response = await axios.post('http://127.0.0.1:5000/incomplete_server_payment/'+ paymentId, { payment });

      if (response.status !== 200) {
        console.error('Incomplete payment error:', response.data.error);
        return;
      }

      // Get and update user balance
      console.log('Incomplete payment found:', response.data);

      // Fetch the updated user balance from the server
      const balanceResponse = await axios.get('http://127.0.0.1:5000/api/user-balance', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('@pi-lotto:access_token')}`,
        },
      });

      if (balanceResponse.status === 200) {
        const updatedBalance = balanceResponse.data.balance;
        // Update the user balance in the parent component (PiLotto)
        onBalanceUpdate(updatedBalance);
      } else {
        console.error('Failed to fetch user balance:', balanceResponse.data.error);
      }
    } catch (error) {
      console.error('Incomplete payment error:', error);
    }
  };

  return (
    <div className="pi-authentication">
      <div className="content">
        <h1 className="title">Pi-Lotto</h1>
        <button
          className={`auth-button ${isAuthenticated ? 'authenticated' : ''}`}
          onClick={handleAuthentication}
          disabled={isAuthenticated}
        >
          {isAuthenticated ? 'Authenticated' : 'Login with Pi Network'}
        </button>
      </div>
    </div>
  );
}

export default PiAuthentication;