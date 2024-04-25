// Lotto.js

import React, { useState, useEffect } from 'react';
import PurchaseModal from './PurchaseModal';
import '../css/Lotto.css';
import axios from 'axios';

function Lotto() {
  const [numbers, setNumbers] = useState(Array(5).fill(null));
  const [PiLotto, setPiLotto] = useState(null);
  const [ticketNumber, setTicketNumber] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [ticketDetails, setTicketDetails] = useState({
    ticketPrice: null,
    baseFee: null,
    serviceFee: null,
  });

  const fetchTicketDetails = async () => {
    try {
      const response = await axios.get('http://127.0.0.1:5000/api/ticket-details', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('@pi-lotto:access_token')}`,
        },
      });
      setTicketDetails(response.data);
    } catch (error) {
      console.error('Error fetching ticket details:', error);
    }
  };

  useEffect(() => {
    if (!ticketNumber && numbers.some((number) => number !== null)) {
      generateTicketNumber();
    }
  }, [numbers, ticketNumber]);

  const generateTicketNumber = () => {
    const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    let ticketNum = '';
    for (let i = 0; i < 8; i++) {
      ticketNum += chars[Math.floor(Math.random() * chars.length)];
    }
    setTicketNumber(ticketNum);
  };

  const handleNumberClick = (number) => {
    const availableIndex = numbers.findIndex((num) => num === null);
    if (availableIndex !== -1) {
      const newNumbers = [...numbers];
      newNumbers[availableIndex] = number;
      setNumbers(newNumbers);
    }
  };

  const handlePiLottoClick = (number) => {
    setPiLotto(number);
  };

  const isNumberDisabled = (number) => {
    return numbers.includes(number);
  };

  const isPiLottoDisabled = (number) => {
    return PiLotto === number;
  };

  const handleNumberUnselect = (number) => {
    const newNumbers = [...numbers];
    const index = newNumbers.indexOf(number);
    if (index !== -1) {
      newNumbers[index] = null;
      setNumbers(newNumbers);
    }
  };

  const handlePiLottoUnselect = () => {
    setPiLotto(null);
  };

  const handleSubmit = async () => {
    // Check if all 5 numbers and the PiLotto number are selected
    const allNumbersSelected = numbers.every((num) => num !== null) && PiLotto !== null;

    if (allNumbersSelected) {
      // Fetch ticket details before showing the modal
      await fetchTicketDetails();

      // Handle ticket purchase logic here
      console.log('Selected numbers:', numbers);
      console.log('PiLotto number:', PiLotto);
      console.log('Ticket number:', ticketNumber);

      setShowModal(true);
    } else {
      alert('Please select all 5 numbers and the PiLotto number to purchase a ticket.');
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
  };

  const numberSets = [];

  if (numbers.every((num) => num !== null) && PiLotto !== null) {
    numberSets.push({
      numbers: numbers,
      PiLotto: PiLotto,
    });
  };

  return (
    <div className="lotto">
      <div className="number-selector-container">
        <div className="number-grid">
          {Array.from({ length: 70 }, (_, i) => (
            <button
              key={i}
              className={`number-button ${isNumberDisabled(i + 1) ? 'disabled' : ''}`}
              onClick={() => handleNumberClick(i + 1)}
              disabled={isNumberDisabled(i + 1)}
            >
              {i + 1}
            </button>
          ))}
        </div>
      </div>
      <div className="lotto-ticket">
        <h3>Your Lotto Ticket</h3>
        <div className="ticket-numbers">
          {numbers.map((number, index) => (
            <span
              key={index}
              className="ticket-number"
              onClick={() => handleNumberUnselect(number)}
            >
              {number || '-'}
            </span>
          ))}
          <span
            className="ticket-PiLotto"
            onClick={() => handlePiLottoUnselect()}
          >
            {PiLotto || '-'}
          </span>
        </div>
        {ticketNumber && <p className="ticket-number-label">Ticket# {ticketNumber}</p>}
        <button className="purchase-button" onClick={handleSubmit}>
          Purchase Ticket
        </button>
      </div>
      <div className="PiLotto-grid">
        <h3>PiLotto</h3>
        {Array.from({ length: 25 }, (_, i) => (
          <button
            key={i}
            className={`PiLotto-button ${isPiLottoDisabled(i + 1) ? 'disabled' : ''}`}
            onClick={() => handlePiLottoClick(i + 1)}
            disabled={isPiLottoDisabled(i + 1)}
          >
            {i + 1}
          </button>
        ))}
      </div>
      {showModal && (
        <PurchaseModal
          numberSets={numberSets}
          ticketNumber={ticketNumber}
          ticketPrice={ticketDetails.ticketPrice}
          baseFee={ticketDetails.baseFee}
          serviceFee={ticketDetails.serviceFee}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
}

export default Lotto;