// PurchaseModal.jsx
import React, { useEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import JsBarcode from 'jsbarcode';
import '../css/PurchaseModal.css';

function PurchaseModal({ numberSets = [], ticketNumber, ticketPrice, baseFee, serviceFee, onClose }) {
  const totalCost = ticketPrice + baseFee + serviceFee;
  const barcodeRef = useRef(null);
  const cardRef = useRef(null);
  const [cardState, setCardState] = useState({
    '--pointer-x': '50%',
    '--pointer-y': '50%',
    '--background-x': '50%',
    '--background-y': '50%',
    // Add more card state variables as needed
  });

  useEffect(() => {
    if (barcodeRef.current) {
      JsBarcode(barcodeRef.current, ticketNumber, {
        format: 'code128',
        width: 2,
        height: 50,
        displayValue: true,
        text: ticketNumber,
        textAlign: 'center',
        textPosition: 'bottom',
        textMargin: 0,
        fontSize: 12,
      });
    }
  }, [ticketNumber]);

  useEffect(() => {
    const card = cardRef.current;

    const handleMouseMove = (e) => {
      // Calculate the mouse position relative to the card
      const { left, top, width, height } = card.getBoundingClientRect();
      const x = ((e.clientX - left) / width) * 100;
      const y = ((e.clientY - top) / height) * 100;

      console.log(x, y);

      // Update the card state variables
      setCardState({
        '--pointer-x': `${x}%`,
        '--pointer-y': `${y}%`,
        '--background-x': `${x}%`,
        '--background-y': `${y}%`,
        // Update other card state variables based on the mouse position
      });
    };

    const handleMouseLeave = () => {
      // Reset the card state variables when the mouse leaves the card
      setCardState({
        '--pointer-x': '50%',
        '--pointer-y': '50%',
        '--background-x': '50%',
        '--background-y': '50%',
        // Reset other card state variables
      });

    };

    card.addEventListener('mousemove', handleMouseMove);
    card.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      card.removeEventListener('mousemove', handleMouseMove);
      card.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, []);

  return ReactDOM.createPortal(
    <div className="modal-overlay">
      <div
        className="modal-content ticket-modal card"
        style={cardState}
        ref={cardRef}
      >
        <div className="card-shine"></div>
        <div className="card-glare"></div>
        <div className="card-rotator">
          <div className="card-front">
            <div className="ticket-header">
              <div className="ticket-pilotto-label">PiLotto</div>
              <div className="ticket-PiLotto-symbol">π</div>
            </div>
            <div className="ticket-numbers-section">
              {numberSets.length > 0 ? (
                numberSets.map((set, index) => (
                  <div key={index} className="ticket-number-set">
                    {set.numbers.map((number, numberIndex) => (
                      <span key={numberIndex} className="ticket-number">
                        {number}
                      </span>
                    ))}
                    <span className="ticket-PiLotto">{set.PiLotto}</span>
                  </div>
                ))
              ) : (
                <p>No number sets available.</p>
              )}
            </div>
            <div className="ticket-details-section">
              <p className="ticket-number-label">Ticket#: {ticketNumber}</p>
              <div className="ticket-cost-section">
                <p>Ticket Price: {ticketPrice} π</p>
                <p>Base Fee: {baseFee} π</p>
                <p>Service Fee: {serviceFee} π</p>
                <p>Total Cost: {totalCost} π</p>
              </div>
            </div>
            <div className="ticket-barcode-section">
              <svg ref={barcodeRef} />
            </div>
          </div>
          <div className="card-back"></div>
        </div>
        <button className="close-button" onClick={onClose}>
          Close
        </button>
      </div>
    </div>,
    document.body
  );
}

export default PurchaseModal;