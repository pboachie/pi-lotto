// PiWithdraw.jsx
import React, { useState } from 'react';
import '../css/PiWithdraw.css';
import { makeApiRequest } from '../utils/api';

const PiWithdraw = ({ onClose, isAuthenticated, userBalance, updateUserBalance }) => {
  const [amount, setAmount] = useState('');
  const [paymentStatus, setPaymentStatus] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [showConfirmation, setShowConfirmation] = useState(false);
  const transactionFee = 0.01;
  const minWithdraw = 0.019;
  const maxWithdraw = userBalance - transactionFee;

  const handleWithdraw = async () => {
    if (!isAuthenticated) {
      setErrorMessage('ERROR: Session expired. Please log in again to withdraw funds.');
      window.location.reload();
      return;
    }

    const parsedAmount = parseFloat(amount);

    if (isNaN(parsedAmount)) {
      setErrorMessage('Please enter a valid number');
      document.querySelector('.pi-withdraw input').select();
      setTimeout(() => {
        setErrorMessage('');
      }, 3000);
      return;
    }

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

    setErrorMessage('');
    setShowConfirmation(true);
  };

  const handleConfirmWithdraw = async () => {
    setShowConfirmation(false);
    setIsLoading(true);

    try {
      const response = await makeApiRequest('post',
        'http://localhost:5000/create_withdrawal',
        {
          amount: parseFloat(amount)
        });

      if (response.status === 200) {
        setPaymentStatus('Withdrawal successful');
        updateUserBalance(response.data.balance);
        setSuccessMessage('Withdrawal processed successfully!. Please check your wallet.');
        setTimeout(() => {
          setSuccessMessage('');
        }, 6000);
        setAmount('');
      }
    } catch (error) {
      alert('Server currently under maintenance. Please try again later.');
      console.error('Error:', error);
    }

    setIsLoading(false);
  };

  const handleCancelWithdraw = () => {
    setShowConfirmation(false);
  };

  return (
    <div className="pi-withdraw">
      <h2>Withdraw {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</h2>
      <div className="balance-info">
        <p>Current Balance: {userBalance.toFixed(3)}</p>
        <p>Max Withdrawal: {maxWithdraw.toFixed(3)}</p>
        <p>Transaction Fee: {transactionFee}</p>
      </div>
      <div className="input-group">
        <input
          type="number"
          placeholder={`Amount (min ${minWithdraw})`}
          value={amount}
          onChange={(e) => {
            setAmount(e.target.value);
            setErrorMessage('');
          }}
          min={minWithdraw}
          max={maxWithdraw}
          step="0.001"
          aria-label="Withdrawal Amount"
          required
          disabled={isLoading}
        />
        <button onClick={handleWithdraw} disabled={!isAuthenticated || isLoading}>
          {isLoading ? 'Processing...' : 'Withdraw'}
        </button>
      </div>
      {errorMessage && (
        <div className="error-message" role="alert">
          {errorMessage}
        </div>
      )}
      {successMessage && (
        <div className="success-message" role="status">
          {successMessage}
        </div>
      )}
      {paymentStatus && <p className="payment-status">Payment Status: {paymentStatus}</p>}
      {showConfirmation && (
        <div className="confirmation-dialog" role="dialog" aria-modal="true">
          <div className="confirmation-content">
            <h3>Confirm Withdrawal</h3>
            <p>Amount: {amount}</p>
            <p>Transaction Fee: {transactionFee}</p>
            <p>Final Amount: {(parseFloat(amount) + transactionFee).toFixed(3)}</p>
            <div className="confirmation-buttons">
              <button onClick={handleConfirmWithdraw}>Confirm</button>
              <button onClick={handleCancelWithdraw}>Cancel</button>
            </div>
          </div>
        </div>
      )}
      {isLoading && (
        <div className="loading-modal">
          <div className="spinner"></div>
          <p>Processing withdrawal. Please wait.</p>
        </div>
      )}
      <button className="close-button" onClick={onClose} disabled={isLoading}>
        Close
      </button>
    </div>
  );
};

export default PiWithdraw;