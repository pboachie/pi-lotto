import React, { useState, useEffect, useRef } from "react";
import PurchaseModal from "./PurchaseModal";
import "../css/Lotto.css";
import { makeApiRequest } from '../utils/api';
import { FaArrowLeft } from 'react-icons/fa';
import AlertBox from '../utils/AlertBox';

function Lotto({ game, onBackToDashboard }) {
  const [numbers, setNumbers] = useState([]);
  const [PiLotto, setPiLotto] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showAlert, setShowAlert] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertTitle, setAlertTitle] = useState('Alert');

  const [ticketDetails, setTicketDetails] = useState({
    ticketPrice: null,    baseFee: null,
    serviceFee: null,     txID: null,
    gameID: null
  });

  const scrollContainerRef = useRef(null);

  useEffect(() => {
    if (game) {
      resetGame();
      const lottoTicket = document.querySelector('.lotto-ticket');
      lottoTicket.style.backgroundImage = `url(${game.game_config.game_image})`;
      lottoTicket.style.backgroundSize = 'cover';
      lottoTicket.style.backgroundRepeat = 'no-repeat';
      lottoTicket.style.backgroundPosition = 'center';
    }
  }, [game]);

  const resetGame = () => {
    setNumbers(Array(5).fill(null));
    setPiLotto(null);
  };

  const fetchTicketDetails = async () => {
    try {
      const game_id = game.id;
      console.log("gameID:", game_id)

      const payload = {
        numbers: numbers,
        PiLotto: PiLotto
      };

      console.log("Numbers selected:", numbers);
      console.log("SuperPi number:", PiLotto);

      const response = await makeApiRequest('put', `http://localhost:5000/api/ticket-details/${game_id}`, payload);
      setTicketDetails(response.data);
    } catch (error) {
      console.error("Error fetching ticket details:", error);
    }
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
    const allNumbersSelected = numbers.every((num) => num !== null) && PiLotto !== null;

    if (allNumbersSelected) {
      await fetchTicketDetails();

      console.log("Selected numbers:", numbers);
      console.log("SuperPi number:", PiLotto);

      setShowModal(true);
    } else {
      setAlertTitle("Warning");
      setAlertMessage("Please select all 6 numbers and the SuperPi number to purchase a ticket.");
      setShowAlert(true);
    }
  };

  const handlePurchaseConfirmation = async () => {
    try {
      const response = await makeApiRequest('post', "http://localhost:5000/api/submit-ticket", ticketDetails);

      console.log("Ticket purchase response:", response);

      setShowModal(false);

      if (response.status === 200) {
        setAlertTitle('Ticket purchased successfully!');
        setAlertMessage('Your ticket has been purchased and submitted. Good luck with your selected numbers!');
      } else {
        setAlertTitle('Error');
        setAlertMessage('Error confirming purchase. Please try again.');
      }
      setShowAlert(true);
    } catch (error) {
      console.error("Error confirming purchase:", error);
      setAlertMessage('Error confirming purchase. Please try again.');
      setShowAlert(true);
    }

    setShowModal(false);
  };

  const handleCloseModal = () => {
    setShowModal(false);
  };

  const handleAlertClose = () => {
    setShowAlert(false);
    resetGame();
  };

  const calculatePrizeAmount = (matchedNumbers, hasPower) => {
    const prizeDistribution = JSON.parse(game.game_config.prize_distribution);
    const key = hasPower ? `${matchedNumbers}_with_power` : `${matchedNumbers}`;
    const prizePercentage = prizeDistribution[key] || 0;
    const prizeAmount = prizePercentage * game.pool_amount;
    return prizeAmount.toFixed(2);  // Format the prize amount to 2 decimal places
  };

  const renderPrizeDistribution = () => {
    const prizeDistribution = JSON.parse(game.game_config.prize_distribution);
    const drawSchedule = JSON.parse(game.game_config.draw_schedule);

    const prizeDistributionMessage = Object.entries(prizeDistribution)
      .map(([key, value]) => {
        const hasPower = key.includes('_with_power');
        const matchedNumbers = hasPower ? key.replace('_with_power', '') : key;
        const prizeAmount = calculatePrizeAmount(matchedNumbers, hasPower);
        return `Match ${matchedNumbers} number${matchedNumbers > 1 ? 's' : ''}${hasPower ? ' with power' : ''}, win ${(value * 100).toFixed(2)}% (${prizeAmount} ${process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'})`;
      })
      .join(', ');

    const drawScheduleMessage = `Draw Schedule: Frequency: ${drawSchedule.frequency}, Day: ${drawSchedule.day}, Time: ${drawSchedule.time}. Distrubution split between winners. Prize pool is ${game.pool_amount.toFixed(2)} ${process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}`; // Format pool amount to 2 decimal places

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
          <p className="pool-amount">{game.pool_amount.toFixed(2)} {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</p> {/* Format pool amount to 2 decimal places */}
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
          ticketNumber={ticketDetails.txID}
          ticketPrice={ticketDetails.ticketPrice}
          baseFee={ticketDetails.baseFee}
          serviceFee={ticketDetails.serviceFee}
          onClose={handleCloseModal}
          onConfirmPurchase={handlePurchaseConfirmation}
        />
      )}
      {showAlert && <AlertBox title={alertTitle} body={alertMessage} onClose={handleAlertClose} />}
    </div>
  );
}

export default Lotto;
