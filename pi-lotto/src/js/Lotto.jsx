// Lotto.js
import React, { useState, useEffect, useRef } from "react";
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

  const scrollContainerRef = useRef(null);

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
      console.log("SuperPi number:", PiLotto);
      console.log("Ticket number:", ticketNumber);

      setShowModal(true);
    } else {
      alert(
        "Please select all 5 numbers and the SuperPi number to purchase a ticket."
      );
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
  };

  const calculatePrizeAmount = (matchedNumbers) => {
    const prizeDistribution = JSON.parse(game.game_config.prize_distribution);
    const prizePercentage = prizeDistribution[`${matchedNumbers}_with_power`] || prizeDistribution[`${matchedNumbers}`] || 0;
    const prizeAmount = prizePercentage * game.pool_amount;
    return prizeAmount.toFixed(2);
  };

  const renderPrizeDistribution = () => {
    const prizeDistribution = JSON.parse(game.game_config.prize_distribution);
    const drawSchedule = JSON.parse(game.game_config.draw_schedule);

    const prizeDistributionMessage = Object.entries(prizeDistribution)
      .map(([key, value]) => {
        const matchedNumbers = key.includes('_with_power') ? key.replace('_with_power', '').split('+').length : parseInt(key);
        const prizeAmount = calculatePrizeAmount(matchedNumbers);
        return `Match ${matchedNumbers} number${matchedNumbers > 1 ? 's' : ''}: ${(value * 100).toFixed(2)}% (${prizeAmount} ${process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'})`;
      })
      .join(', ');

    const drawScheduleMessage = `Draw Schedule: Frequency: ${drawSchedule.frequency}, Day: ${drawSchedule.day}, Time: ${drawSchedule.time}`;

    return (
      <div className="game-details-scrollable" ref={scrollContainerRef}>
        <div className="game-details-scroll-content">
          <p>{prizeDistributionMessage}, {drawScheduleMessage}</p>
        </div>
      </div>
    );
  };

  useEffect(() => {
    const scrollContainer = scrollContainerRef.current;
    if (scrollContainer) {
      const scrollInterval = setInterval(() => {
        scrollContainer.scrollLeft += 1;
        if (scrollContainer.scrollLeft + scrollContainer.offsetWidth >= scrollContainer.scrollWidth) {
          scrollContainer.scrollLeft = 0;
        }
      }, 50);

      return () => clearInterval(scrollInterval);
    }
  }, []);

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
        {renderPrizeDistribution()}
        <div className="number-selector-container">
          <div className="PiLotto-grid">
            <h3>SuperPi Numbers:</h3>
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
