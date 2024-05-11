// PiLottoDashboard.js

import React, { useEffect, useState } from "react";
import "../css/PiLottoDashboard.css";
import { makeApiRequest } from '../utils/api';
import Lotto from './Lotto';


function PiLottoDashboard() {
  const [games, setGames] = useState([]);
  const [selectedGame, setSelectedGame] = useState(null);

  useEffect(() => {
    fetchGames();
  }, []);

  const fetchGames = async () => {
    try {
      const response = await makeApiRequest('get', "http://localhost:5000/api/games");
      setGames(response.data.games);

      // Save the first game to local storage
      if (response.data.games.length > 0) {
        localStorage.setItem("@pi-lotto-selectedGame", JSON.stringify(response.data.games[0]));
      }
    } catch (error) {
      console.error("Error fetching games:", error);
    }
  };

  const handleGameClick = (game) => {
    console.log("Loading game with ID:", game.id);
    localStorage.setItem("@pi-lotto-selectedGame", JSON.stringify(game));
    setSelectedGame(game);
  };

  const handleBackToDashboard = () => {
    setSelectedGame(null);
  };

  if (selectedGame) {
    return <Lotto game={selectedGame} onBackToDashboard={handleBackToDashboard} />;
  }

  return (
    <div className="pi-lotto-dashboard">
      <h2>Pi-Lotto Games</h2>
      <div className="game-list">
        {games.map((game) => {
          const drawSchedule = JSON.parse(game.game_config.draw_schedule);
          return (
            <div key={game.id} className="game-card" onClick={() => handleGameClick(game)}>
              <img src={game.game_config.game_image} alt={game.name} className="game-image" />
              <div className="game-info">
                <h3>{game.name}</h3>
                <div className="game-details">
                  <p>Entry Fee: {game.entry_fee} {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</p>
                  <p>Current Pool: {game.pool_amount} {process.env.NODE_ENV === 'production' ? 'π' : 'Test-π'}</p>
                </div>
                <div className="draw-schedule">
                  <p>
                    Draw: {drawSchedule.day} at <strong>{drawSchedule.time}</strong>
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default PiLottoDashboard;
