// PiWithdraw.jsx
import React, { useState } from 'react';
import axios from 'axios';
import '../css/PiWithdraw.css';

const PiWithdraw = ({ onClose, isAuthenticated, userBalance, updateUserBalance }) => {
  const [amount, setAmount] = useState('');
  const [paymentStatus, setPaymentStatus] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
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
      setIsLoading(true); // Set loading state to true before making the API request
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
        setIsLoading(false);
        setSuccessMessage('Withdrawal processed successfully!'); // Set success message
        setTimeout(() => {
          setSuccessMessage(''); // Clear success message after 3 seconds
        }, 3000);
      }else {
        setPaymentStatus('Withdrawal failed');
        setErrorMessage(response.data.error);
        setIsLoading(false); // Set loading state to false in case of an error
        setTimeout(() => {
          setErrorMessage('');
        }, 3000);
      }
    } catch (error) {
      alert('Server currently under maintenance. Please try again later.');
      setErrorMessage(error.message);
      console.error('Error:', error);
      setIsLoading(false); // Set loading state to false in case of an error
      setTimeout(() => {
        setErrorMessage('');
      }, 3000);
    }
  };

  const handleWithdrawClick = () => {
    setShowConfirmation(true);
  };

  const handleConfirmWithdraw = async () => {
    setShowConfirmation(false);
    await handleWithdraw();
  };

  const handleCancelWithdraw = () => {
    setShowConfirmation(false);
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
        {isLoading ? (
          <div className="loading-spinner">Processing...</div>
        ) : (
          <button onClick={handleWithdrawClick} disabled={!isAuthenticated}>
            Withdraw
          </button>
        )}
      </div>
      {showConfirmation && (
        <div className="confirmation-dialog">
          <div className="confirmation-content">
            <h3>Confirm Withdrawal</h3>
            <p>Amount: {amount}</p>
            <p>Transaction Fee: {transactionFee}</p>
            <p>Final Amount: {(parseFloat(amount) + transactionFee).toFixed(6)}</p>
            <div className="confirmation-buttons">
              <button onClick={handleConfirmWithdraw}>Confirm</button>
              <button onClick={handleCancelWithdraw}>Cancel</button>
            </div>
          </div>
        </div>
      )}
      {errorMessage && <div className="error-message">{errorMessage}</div>}
      {successMessage && (
        <div className="success-message">{successMessage}</div>
      )}
      {paymentStatus && <p className="payment-status">Payment Status: {paymentStatus}</p>}
      <button className="close-button" onClick={onClose}>
        Close
      </button>
    </div>
  );
};

export default PiWithdraw;