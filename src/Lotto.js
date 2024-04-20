import React, { useState, useEffect } from 'react';
import './Lotto.css';

function Lotto() {
  const [numbers, setNumbers] = useState(Array(5).fill(null));
  const [powerball, setPowerball] = useState(null);
  const [ticketNumber, setTicketNumber] = useState('');

  useEffect(() => {
    if (numbers.some((number) => number !== null)) {
      generateTicketNumber();
    } else {
      setTicketNumber('');
    }
  }, [numbers]);

  const generateTicketNumber = () => {
    const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    let ticketNum = '';
    for (let i = 0; i < 8; i++) {
      ticketNum += chars[Math.floor(Math.random() * chars.length)];
    }
    setTicketNumber(ticketNum);
  };

  const handleNumberChange = (index, value) => {
    const newNumbers = [...numbers];
    newNumbers[index] = value;
    setNumbers(newNumbers);
  };

  const handlePowerballChange = (value) => {
    setPowerball(value);
  };

  const handleSubmit = () => {
    // Handle ticket purchase logic here
    console.log('Selected numbers:', numbers);
    console.log('Powerball number:', powerball);
    console.log('Ticket number:', ticketNumber);
  };

  return (
    <div className="lotto">
      <h2>Select Your Numbers</h2>
      <div className="number-selectors">
        {numbers.map((number, index) => (
          <select
            key={index}
            value={number || ''}
            onChange={(e) => handleNumberChange(index, parseInt(e.target.value))}
          >
            <option value="">Select</option>
            {Array.from({ length: 70 }, (_, i) => (
              <option key={i} value={i + 1}>
                {i + 1}
              </option>
            ))}
          </select>
        ))}
      </div>
      <h2>Select Powerball Number</h2>
      <div className="powerball-selector">
        <select
          value={powerball || ''}
          onChange={(e) => handlePowerballChange(parseInt(e.target.value))}
        >
          <option value="">Select</option>
          {Array.from({ length: 25 }, (_, i) => (
            <option key={i} value={i + 1}>
              {i + 1}
            </option>
          ))}
        </select>
      </div>
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
    </div>
  );
}

export default Lotto;