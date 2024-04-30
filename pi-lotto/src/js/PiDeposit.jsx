import React, { useState } from 'react';
import axios from 'axios';
import '../css/PiDeposit.css';

const PiDeposit = ({ onClose, isAuthenticated }) => {
  const [amount, setAmount] = useState('');
  const [paymentStatus, setPaymentStatus] = useState('');

  const handleDeposit = async () => {
    if (!isAuthenticated) {
      console.error('User not authenticated');
      return;
    }

    const parsedAmount = parseFloat(amount);
    if (parsedAmount < 0.25) {
      console.error('Amount must be at least 0.25');
      return;
    }

    const transID = Math.floor(Math.random() * 1000000000);

    try {
      const paymentData = {
        amount: parsedAmount,
        memo: 'Deposit to Pi-Lotto',
        metadata: {
          locTransID: transID,
          dateCreated: new Date().toISOString(),
        },
      };

      const callbacks = {
        onReadyForServerApproval: async (paymentId) => {
          const paymentData = {
            paymentId,
            amount: parsedAmount,
            memo: 'Deposit to Pi-Lotto',
            metadata: {
              locTransID: transID,
              dateCreated: new Date().toISOString(),
            },
          };

          try {
            // Send the payment data to the backend for server-side approval
            const response = await axios.post('http://localhost:5000/api/approve_payment', paymentData);
            console.log('Payment approved:', response);
          } catch (error) {
            console.error('Payment approval error:', error);
            setPaymentStatus('error');
          }
        },
        onReadyForServerCompletion: async (paymentId, txid) => {
          try {
            // Send the paymentId and txid to the backend for server-side completion
            const response = await axios.post('http://localhost:5000/api/complete_payment', { paymentId, txid });
            console.log('Payment completed:', response);
            setPaymentStatus('completed');
          } catch (error) {
            console.error('Payment completion error:', error);
            setPaymentStatus('error');
          }
        },
        onCancel: (paymentId) => {
          console.log('Payment cancelled:', paymentId);
          setPaymentStatus('cancelled');
        },
        onError: (error, payment) => {
          console.error('Payment error:', payment);
          console.error('Payment error:', error);
          setPaymentStatus('error');
        },
      };

      const Pi = window.Pi;
      Pi.createPayment(paymentData, callbacks);
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
      {paymentStatus && <p className="payment-status">Payment Status: {paymentStatus}</p>}
      <button className="close-button" onClick={onClose}>
        Close
      </button>
    </div>
  );
};

export default PiDeposit;