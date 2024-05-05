// PiWithdraw.jsx
import React, { useState } from 'react';
import axios from 'axios';
import '../css/PiWithdraw.css';

const PiWithdraw = ({ onClose, isAuthenticated, userBalance, updateUserBalance }) => {
  const [amount, setAmount] = useState('');
  const [paymentStatus, setPaymentStatus] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const transactionFee = 0.01;
  const minWithdraw = 0.019;
  const maxWithdraw = userBalance - transactionFee;

  const handleWithdraw = async () => {
    if (!isAuthenticated) {
      console.error('User not authenticated');
      return;
    }

    const parsedAmount = parseFloat(amount);

    if (parsedAmount && !isNaN(parsedAmount)) {
      if (parsedAmount < minWithdraw) {
        setErrorMessage(`Amount must be at least ${minWithdraw}`);
        document.querySelector('.pi-withdraw input').select();
        setTimeout(() => {
          setErrorMessage('');
        }, 3000);
        return;
      }

      if (parsedAmount > maxWithdraw) {
        setErrorMessage(`Amount cannot exceed ${maxWithdraw}`);
        document.querySelector('.pi-withdraw input').select();
        setTimeout(() => {
          setErrorMessage('');
        }, 3000);
        return;
      }
    } else {
      setErrorMessage('Please enter a valid amount to withdraw');
      document.querySelector('.pi-withdraw input').focus();
      setTimeout(() => {
        setErrorMessage('');
      }, 3000);
      return;
    }

    const transID = Math.floor(Math.random() * 1000000000);

    try {
      const response = await axios.post(
        'http://localhost:5000/api/withdraw',
        {
          amount: parsedAmount,
          transID,
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('@pi-lotto:access_token')}`,
          },
        }
      );

      if (response.status === 200) {
        setPaymentStatus('Withdrawal successful');
        updateUserBalance(response.data.balance);
        setAmount('');
      }
    } catch (error) {
      alert('Server currently under maintenance. Please try again later.');
      console.error('Error:', error);
    }
  };

  return (
    <div className="pi-withdraw">
      <h2>Withdraw {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</h2>
      <div className="balance-info">
        <p>Current Balance: {userBalance.toFixed(6)}</p>
        <p>Max Withdrawal: {maxWithdraw.toFixed(6)}</p>
        <p>Network Fee: {transactionFee}</p>
      </div>
      <div className="input-group">
        <input
          type="number"
          placeholder={`Amount (min ${minWithdraw})`}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          min={minWithdraw}
          max={maxWithdraw}
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