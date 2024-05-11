// PiAuthentication.js
import React, { useEffect, useState } from 'react';
import '../css/PiAuthentication.css';
import { makeApiRequest } from '../utils/api';
import axios from 'axios';


function PiAuthentication({ onAuthentication, isAuthenticated, onBalanceUpdate }) {
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
      const response = await axios.post('http://localhost:5000/signin', { authResult });


      // Return false if status is not 200
      if (response.status !== 200) {
        return false;
      }

      // Save the access token to the local storage
      if (response.data.access_token && response.data.refresh_token) {
        localStorage.setItem('@pi-lotto:access_token', response.data.access_token);
        localStorage.setItem('@pi-lotto:refresh_token', response.data.refresh_token);
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
      const response = await makeApiRequest('post', 'http://localhost:5000/incomplete/'+ paymentId, { payment });

      if (response.status !== 200) {
        console.error('Incomplete payment error:', response.data.error);
        return;
      }

      // Get and update user balance
      console.log('Incomplete payment found:', response.data);

      // Fetch the updated user balance from the server
      const balanceResponse = await makeApiRequest('get', 'http://localhost:5000/api/user-balance', {
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

  useEffect(() => {
    const generateShapes = () => {
      const backgroundShapes = document.querySelector('.background-shapes');
      const numShapes = Math.floor(Math.random() * 5) + 4; // Generate a random number between 4 and 8

      for (let i = 0; i < numShapes; i++) {
        const shape = document.createElement('div');
        shape.classList.add('shape');

        const shapeSize = Math.floor(Math.random() * 100) + 50; // Generate a random size between 50px and 150px
        shape.style.width = `${shapeSize}px`;
        shape.style.height = `${shapeSize}px`;

        const screenWidth = window.innerWidth;
        const screenHeight = window.innerHeight;

        const shapeTop = Math.floor(Math.random() * screenHeight);
        const shapeLeft = Math.floor(Math.random() * screenWidth);

        shape.style.top = `${shapeTop}px`;
        shape.style.left = `${shapeLeft}px`;

        const animationDelay = Math.random() * 10; // Generate a random animation delay between 0s and 10s
        shape.style.animationDelay = `${animationDelay}s`;

        backgroundShapes.appendChild(shape);
      }
    };

    generateShapes();
  }, []);


  return (
    <div className="pi-authentication">
      <div className="content">
        <h1 className="title">Welcome to UNI PI GAMES</h1>
        <p className="description">Play and win Pi coins!</p>
        <div className="auth-button-container">
          <button
            className={`auth-button ${isAuthenticated ? 'authenticated' : ''}`}
            onClick={handleAuthentication}
            disabled={isAuthenticated || isAuthenticating}
          >
            {isAuthenticating ? 'Authenticating with Pi Network...' : 'Login with Pi Network'}
          </button>
          <div className="auth-button-background"></div>
        </div>
      </div>
      <div className="background-shapes"></div>
    </div>
  );
}

export default PiAuthentication;