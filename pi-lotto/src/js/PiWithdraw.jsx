// PiWithdraw.jsx
import React, { useState } from 'react';
import axios from 'axios';
import '../css/PiWithdraw.css';

const PiWithdraw = ({ onClose, isAuthenticated, userBalance, updateUserBalance }) => {
  const [amount, setAmount] = useState('');
  const [paymentStatus, setPaymentStatus] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const handleWithdraw = async () => {
    if (!isAuthenticated) {
      console.error('User not authenticated');
      return;
    }

    const parsedAmount = parseFloat(amount);

    // Check if number is not null or blank and is numeric (TODO - Fetch minimum withdrawal amount from the server)
    if (parsedAmount && !isNaN(parsedAmount)) {
      if (parsedAmount < 0.019) {
        setErrorMessage('Amount must be at least 0.019');
        document.querySelector('.pi-withdraw input').select();
        setTimeout(() => {
          setErrorMessage('');
        }, 3000); // Clear the error message after 3 seconds
        return;
      }
    } else {
      setErrorMessage('Please enter an amount to withdraw');
      document.querySelector('.pi-withdraw input').focus();
      setTimeout(() => {
        setErrorMessage('');
      }, 3000); // Clear the error message after 3 seconds
      return;
    }


    // const fetchUserBalance = async () => {
    //   try {
    //     const response = await axios.get('http://localhost:5000/api/user-balance', {
    //       headers: {
    //         Authorization: `Bearer ${localStorage.getItem('@pi-lotto:access_token')}`,
    //       },
    //     });

    //     if (response.status === 200) {
    //       return response.data.balance;
    //     } else {
    //       console.error('Failed to fetch user balance:', response.data.error);
    //       return null;
    //     }
    //   } catch (error) {
    //     console.error('Error fetching user balance:', error);
    //     return null;
    //   }
    // };

    const transID = Math.floor(Math.random() * 1000000000);

    try {
      // Withdraw the amount from the user balance [TODO: FINISH AND TEST LOGIC]
        const response = await axios.post('http://localhost:5000/api/withdraw', {
            amount: parsedAmount,
            transID,
        }, {
            headers: {
            Authorization: `Bearer ${localStorage.getItem('@pi-lotto:access_token')}`,
            },
        });

        if (response.status === 200) {
            setPaymentStatus('Withdrawal successful');
            // Update the user balance in the parent component (PiLotto)
            updateUserBalance(response.data.balance);
        }
    }
    catch (error) {
        alert('Server currently under maintenance. Please try again later.');
        console.error('Error:', error);
    }
  };

  return (
    <div className="pi-withdraw">
      <h2>Withdraw {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</h2>
      <div className="input-group">
        <input
          type="number"
          placeholder="Amount (min 0.019)"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          min="0.019"
          step="0.001"
        />
        <button onClick={handleWithdraw} disabled={!isAuthenticated}>
          Withdraw
        </button>
      </div>
      {errorMessage && <div className="error-message">{errorMessage}</div>}
      {paymentStatus && <p className="payment-status">Payment Status: {paymentStatus}</p>}
      <button className="close-button" onClick={onClose}>
        Close
      </button>
    </div>
  );
};

export default PiWithdraw;