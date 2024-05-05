// PiDeposit.jsx
import React, { useState } from 'react';
import axios from 'axios';
import '../css/PiDeposit.css';

const PiDeposit = ({ onClose, isAuthenticated, userBalance, updateUserBalance }) => {
  const [amount, setAmount] = useState('');
  const [paymentStatus, setPaymentStatus] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [showConfirmation, setShowConfirmation] = useState(false);
  const minDeposit = 0.25;

  const handleDeposit = async () => {
    if (!isAuthenticated) {
      setErrorMessage('User not authenticated');
      window.location.reload();
      return;
    }

    const parsedAmount = parseFloat(amount);

    if (isNaN(parsedAmount)) {
      setErrorMessage('Please enter a valid number');
      document.querySelector('.pi-deposit input').select();
      setTimeout(() => {
        setErrorMessage('');
      }, 3000);
      return;
    }

    if (parsedAmount < minDeposit) {
      setErrorMessage(`Amount must be at least ${minDeposit}`);
      document.querySelector('.pi-deposit input').select();
      setTimeout(() => {
        setErrorMessage('');
      }, 3000);
      return;
    }

    setErrorMessage('');
    setShowConfirmation(true);
  };

  const handleConfirmDeposit = async () => {
    setShowConfirmation(false);
    setIsLoading(true);

    const fetchUserBalance = async () => {
      try {
        const response = await axios.get('http://localhost:5000/api/user-balance', {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('@pi-lotto:access_token')}`,
          },
        });

        if (response.status === 200) {
          return response.data.balance;
        } else {
          console.error('Failed to fetch user balance:', response.data.error);
          return null;
        }
      } catch (error) {
        console.error('Error fetching user balance:', error);
        return null;
      }
    };

    const transID = Math.floor(Math.random() * 1000000000);

    try {
      const paymentData = {
        amount: parseFloat(amount),
        memo: 'Deposit to Pi-Lotto',
        metadata: {
          locTransID: transID,
          dateCreated: new Date().toISOString(),
          transType: 'deposit',
        },
      };

      const callbacks = {
        onReadyForServerApproval: async (paymentId) => {
          try {
            const header = {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${localStorage.getItem('@pi-lotto:access_token')}`,
            };

            // Send the payment data to the backend for server-side approval
            const response = await axios.post(
              `http://localhost:5000/approve_payment/${paymentId}`,
              { paymentData },
              { headers: header }
            );

            if (response.status !== 200) {
              console.error('Payment approval error:', response.data.error);
              setPaymentStatus('ERROR: ' + response.data.error);
              setIsLoading(false);
              return false;
            }

            console.log('Payment approved:', response.data);
            setPaymentStatus('Completing payment...');
            return true;
          } catch (error) {
            console.error('Payment approval error:', error);
            setPaymentStatus('error');
            setIsLoading(false);
          }
        },
        onReadyForServerCompletion: async (paymentId, txid) => {
          try {
            const header = {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${localStorage.getItem('@pi-lotto:access_token')}`,
            };

            console.log('Payment ID:', paymentId);
            console.log('TXID:', txid);

            const response = await axios.post(
              `http://localhost:5000/complete_payment/${paymentId}`,
              { paymentId, txid },
              { headers: header }
            );

            if (response.status !== 200) {
              console.error('Payment completion error:', response.data.error);
              setPaymentStatus('ERROR: ' + response.data.error);
              await window.Pi.cancelPayment(paymentId);
              setIsLoading(false);
              return false;
            }

            console.log('Payment completed:', response.data);
            setPaymentStatus('Payment Transfer Complete!');

            const updatedBalance = await fetchUserBalance();
            if (updatedBalance !== null) {
              updateUserBalance(updatedBalance);
              setSuccessMessage('Deposit processed successfully!');
              setTimeout(() => {
                setSuccessMessage('');
              }, 3000);
            }

            setAmount('');
            setIsLoading(false);
            return true;
          } catch (error) {
            console.error('Payment completion error:', error);
            setPaymentStatus('error');
            setIsLoading(false);
          }
        },
        onCancel: (paymentId) => {
          console.log('Payment cancelled:', paymentId);
          setPaymentStatus('Payment cancelled');
          setIsLoading(false);
        },
        onError: (error, payment) => {
          console.error('Payment error:', payment);
          console.error('Payment error:', error);
          setPaymentStatus('error');
          setIsLoading(false);
        },
      };

      const paymentId = await window.Pi.createPayment(paymentData, callbacks);
      console.log('Payment created with ID:', paymentId);
    } catch (error) {
      console.error('Error:', error);
      setIsLoading(false);
    }
  };

  const handleCancelDeposit = () => {
    setShowConfirmation(false);
  };

  return (
    <div className="pi-deposit">
      <h2>Deposit {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</h2>
      <div className="input-group">
        <input
          type="number"
          placeholder={`Amount (min ${minDeposit})`}
          value={amount}
          onChange={(e) => {
            setAmount(e.target.value);
            setErrorMessage('');
          }}
          min={minDeposit}
          step="0.001"
          aria-label="Deposit Amount"
          required
        />
        <button onClick={handleDeposit} disabled={!isAuthenticated || isLoading}>
          {isLoading ? 'Processing...' : 'Deposit'}
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
            <h3>Confirm Deposit</h3>
            <p>Amount: {amount}</p>
            <div className="confirmation-buttons">
              <button onClick={handleConfirmDeposit}>Confirm</button>
              <button onClick={handleCancelDeposit}>Cancel</button>
            </div>
          </div>
        </div>
      )}
      <button className="close-button" onClick={onClose}>
        Close
      </button>
    </div>
  );
};

export default PiDeposit;