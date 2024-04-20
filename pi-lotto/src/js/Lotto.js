import React, { useState, useEffect } from 'react';
import '../css/Lotto.css';

function Lotto() {
  const [numbers, setNumbers] = useState(Array(5).fill(null));
  const [powerball, setPowerball] = useState(null);
  const [ticketNumber, setTicketNumber] = useState('');

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

  const handlePowerballClick = (number) => {
    setPowerball(number);
  };

  const isNumberDisabled = (number) => {
    return numbers.includes(number);
  };

  const isPowerballDisabled = (number) => {
    return powerball === number;
  };

  const handleSubmit = () => {
    // Handle ticket purchase logic here
    console.log('Selected numbers:', numbers);
    console.log('Powerball number:', powerball);
    console.log('Ticket number:', ticketNumber);
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
      <div className="lotto-ticket-container">
        <div className="lotto-ticket">
          <h3>Your Lotto Ticket</h3>
          <div className="ticket-numbers">
            {numbers.map((number, index) => (
              <span key={index} className="ticket-number">
                {number || '-'}
              </span>
            ))}
            <span className="ticket-powerball">{powerball || '-'}</span>
          </div>
          {ticketNumber && <p className="ticket-number-label">Ticket# {ticketNumber}</p>}
          <button className="purchase-button" onClick={handleSubmit}>
            Purchase Ticket
          </button>
        </div>
        <div className="powerball-grid">
          <h3>Powerball</h3>
          {Array.from({ length: 25 }, (_, i) => (
            <button
              key={i}
              className={`powerball-button ${isPowerballDisabled(i + 1) ? 'disabled' : ''}`}
              onClick={() => handlePowerballClick(i + 1)}
              disabled={isPowerballDisabled(i + 1)}
            >
              {i + 1}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Lotto;