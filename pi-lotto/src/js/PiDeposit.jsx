// PiDeposit.jsx
import React, { useState } from 'react';
import axios from 'axios';
import '../css/PiDeposit.css';

const PiDeposit = ({ onClose, isAuthenticated, userBalance, setUserBalance }) => {
  const [amount, setAmount] = useState('');
  const [paymentStatus, setPaymentStatus] = useState('');
  const [errorMessage, setErrorMessage] = useState('');


  const handleDeposit = async () => {
    if (!isAuthenticated) {
      console.error('User not authenticated');
      return;
    }

    const parsedAmount = parseFloat(amount);
    if (parsedAmount < 0.25) {
      setErrorMessage('Amount must be at least 0.25');
      setTimeout(() => {
        setErrorMessage('');
      }, 3000); // Clear the error message after 3 seconds
      return;
    }

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
        amount: parsedAmount,
        memo: 'Deposit to Pi-Lotto',
        metadata: {
          locTransID: transID,
          dateCreated: new Date().toISOString(),
          transType: 'deposit'
        },
      };

      const callbacks = {
        onReadyForServerApproval: async (paymentId) => {

          try {

            const header = {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ' + localStorage.getItem('@pi-lotto:access_token')
            }

            console.log()

            // Send the payment data to the backend for server-side approval
            const response = await axios.post('http://127.0.0.1:5000/approve_payment/'+ paymentId, { paymentData }, { headers: header });

            if (response.status !== 200) {
              console.error('Payment approval error:', response.data.error);
              setPaymentStatus('ERROR: ' + response.data.error);
              return false;
            }

            // const response = await window.Pi.getPayment(paymentId);
            console.log('Payment approved:', response.data);
            setPaymentStatus('Completing payment...');
            return true;

          } catch (error) {
            console.error('Payment approval error:', error);
            setPaymentStatus('error');
          }
        },
        onReadyForServerCompletion: async (paymentId, txid) => {
          try {
            // Send the paymentId and txid to the backend for server-side completion
            const header = {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ' + localStorage.getItem('@pi-lotto:access_token')
            }

            console.log('Payment ID:', paymentId);
            console.log('TXID:', txid);

            const response = await axios.post('http://127.0.0.1:5000/complete_payment/'+ paymentId, { paymentId, txid }, { headers: header });

            if (response.status !== 200) {
              console.error('Payment completion error:', response.data.error);
              setPaymentStatus('ERROR: ' + response.data.error);

              // Cancel the payment
              await window.Pi.cancelPayment(paymentId);
              return false;
            }

            console.log('Payment completed:', response.data);
            setPaymentStatus('Payment Transfer Complete!');

            // Update the user balance
            const updatedBalance = await fetchUserBalance();
            if (updatedBalance !== null) {
              setUserBalance(updatedBalance);
            }

            // Clear form input
            setAmount('');

            return true;
          } catch (error) {
            console.error('Payment completion error:', error);
            setPaymentStatus('error');
          }
        },
        onCancel: (paymentId) => {
          console.log('Payment cancelled:', paymentId);
          setPaymentStatus('Payment cancelled');
        },
        onError: (error, payment) => {
          console.error('Payment error:', payment);
          console.error('Payment error:', error);
          setPaymentStatus('error');
        },
      };

      const paymentId = await window.Pi.createPayment(paymentData, callbacks);
      console.log('Payment created with ID:', paymentId);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <div className="pi-deposit">
      <h2>Deposit {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</h2>
      <div className="input-group">
        <input
          type="number"
          placeholder="Amount (min 0.25)"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          min="0.25"
          step="0.01"
        />
        <button onClick={handleDeposit} disabled={!isAuthenticated}>
          Deposit
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

export default PiDeposit;