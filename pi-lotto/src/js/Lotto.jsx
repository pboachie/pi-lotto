// Lotto.js
import React, { useState, useEffect } from "react";
import PurchaseModal from "./PurchaseModal";
import "../css/Lotto.css";
import { makeApiRequest } from '../utils/api';
import { FaArrowLeft } from 'react-icons/fa';

function Lotto({ game, onBackToDashboard }) {
  const [numbers, setNumbers] = useState([]);
  const [PiLotto, setPiLotto] = useState(null);
  const [ticketNumber, setTicketNumber] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [ticketDetails, setTicketDetails] = useState({
    ticketPrice: null,    baseFee: null,
    serviceFee: null,
  });

  useEffect(() => {
    if (game) {
      setNumbers(Array(5).fill(null));
    }
  }, [game]);

  const fetchTicketDetails = async () => {
    try {
      const response = await makeApiRequest('get', "http://localhost:5000/api/ticket-details", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("@pi-lotto:access_token")}`,
        },
      });
      setTicketDetails(response.data);
    } catch (error) {
      console.error("Error fetching ticket details:", error);
    }
  };

  useEffect(() => {
    if (!ticketNumber && numbers.some((number) => number !== null)) {
      generateTicketNumber();
    }
  }, [numbers, ticketNumber]);

  const generateTicketNumber = () => {
    const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    let ticketNum = "";
    for (let i = 0; i < 8; i++) {
      ticketNum += chars[Math.floor(Math.random() * chars.length)];
    }
    setTicketNumber(ticketNum);
  };

  const handleNumberClick = (number) => {
    if (!isNumberDisabled(number)) {
      const availableIndex = numbers.findIndex((num) => num === null);
      if (availableIndex !== -1) {
        const newNumbers = [...numbers];
        newNumbers[availableIndex] = number;
        setNumbers(newNumbers);
      }
    }
  };

  const handlePiLottoClick = (number) => {
    if (!isNumberDisabled(number)) {
      setPiLotto(number);
    }
  };

  const isNumberDisabled = (number) => {
    return numbers.includes(number) || PiLotto === number || numbers.filter((num) => num !== null).length >= 6;
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
    const allNumbersSelected =
      numbers.every((num) => num !== null) && PiLotto !== null;

    if (allNumbersSelected) {
      // Fetch ticket details before showing the modal
      await fetchTicketDetails();

      // Handle ticket purchase logic here
      console.log("Selected numbers:", numbers);
      console.log("PiLotto number:", PiLotto);
      console.log("Ticket number:", ticketNumber);

      setShowModal(true);
    } else {
      alert(
        "Please select all 5 numbers and the PiLotto number to purchase a ticket."
      );
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
  }

  if (!game) {
    return <div>Loading...</div>;
  }

  const numberRange = JSON.parse(game.game_config.number_range);
  const mainNumberRange = numberRange.main;
  const powerNumberRange = numberRange.power;
  const prizeDistribution = JSON.parse(game.game_config.prize_distribution);
  const drawSchedule = JSON.parse(game.game_config.draw_schedule);

  return (
    <div className="lotto">
      <div className="top-bar">
        <button className="back-button" onClick={onBackToDashboard}>
          <FaArrowLeft /> Back
        </button>
        <div className="pool-size">
          <h3>Current Pool Size</h3>
          <p className="pool-amount">{game.pool_amount} {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</p>
        </div>
      </div>
      <div className="lotto-container">
        <div className="lotto-ticket">
          <h3>{game.name}</h3>
          <div className="ticket-numbers">
            {numbers.map((number, index) => (
              <span
                key={index}
                className={`ticket-number ${number ? "selected" : ""}`}
                onClick={() => handleNumberUnselect(number)}
              >
                {number || "-"}
              </span>
            ))}
            <span
              className={`ticket-PiLotto ${PiLotto ? "selected" : ""}`}
              onClick={() => handlePiLottoUnselect()}
            >
              {PiLotto || "-"}
            </span>
          </div>
          {ticketNumber && <p className="ticket-number-label">Ticket# {ticketNumber}</p>}
          <button className="purchase-button" onClick={handleSubmit}>
            Purchase Ticket
          </button>
        </div>
        <div className="game-details">
          <div className="prize-distribution">
            <h3>Prize Distribution</h3>
            <ul>
              {Object.entries(prizeDistribution).map(([key, value]) => (
                <li key={key}>
                  {key.replace(/_/g, ' + ')}: {(value * 100).toFixed(2)}%
                </li>
              ))}
            </ul>
          </div>
          <div className="fees">
            <h3>Fees</h3>
            <p>Entry Fee: {game.entry_fee} {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</p>
            <p>Service Fee: {ticketDetails.serviceFee} {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</p>
            <p>Base Fee: {ticketDetails.baseFee} {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</p>
          </div>
          <div className="draw-schedule">
            <h3>Draw Schedule</h3>
            <p>Frequency: {drawSchedule.frequency}</p>
            <p>Day: {drawSchedule.day}</p>
            <p>Time: {drawSchedule.time}</p>
          </div>
        </div>
        <div className="number-selector-container">
          <div className="PiLotto-grid">
            <h3>PiLotto</h3>
            {Array.from({ length: powerNumberRange[1] - powerNumberRange[0] + 1 }, (_, i) => (
              <button
                key={i}
                className={`PiLotto-button ${isPiLottoDisabled(i + powerNumberRange[0]) ? "disabled" : ""} ${
                  PiLotto === i + powerNumberRange[0] ? "selected" : ""
                }`}
                onClick={() => handlePiLottoClick(i + powerNumberRange[0])}
                disabled={isPiLottoDisabled(i + powerNumberRange[0])}
              >
                {i + powerNumberRange[0]}
              </button>
            ))}
          </div>
          <div className="number-grid">
            {Array.from({ length: mainNumberRange[1] - mainNumberRange[0] + 1 }, (_, i) => (
              <button
                key={i}
                className={`number-button ${isNumberDisabled(i + mainNumberRange[0]) ? "disabled" : ""} ${
                  numbers.includes(i + mainNumberRange[0]) ? "selected" : ""
                }`}
                onClick={() => handleNumberClick(i + mainNumberRange[0])}
                disabled={isNumberDisabled(i + mainNumberRange[0])}
              >
                {i + mainNumberRange[0]}
              </button>
            ))}
          </div>
        </div>
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
