// PurchaseModal.jsx
import React, { useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import JsBarcode from 'jsbarcode';
import '../css/PurchaseModal.css';

function PurchaseModal({ numberSets = [], ticketNumber, ticketPrice, baseFee, serviceFee, onClose }) {
  const totalCost = ticketPrice + baseFee + serviceFee;
  const barcodeRef = useRef(null);

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

  return ReactDOM.createPortal(
    <div className="modal-overlay">
      <div className="modal-content ticket-modal">
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
        <button className="close-button" onClick={onClose}>
          Close
        </button>
      </div>
    </div>,
    document.body
  );
}

export default PurchaseModal;