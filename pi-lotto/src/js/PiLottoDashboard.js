// PiLottoDashboard.js
import React, { useEffect, useState } from "react";
import axios from "axios";
import "../css/PiLottoDashboard.css";

function PiLottoDashboard() {
  const [games, setGames] = useState([]);

  useEffect(() => {
    fetchGames();
  }, []);

  const fetchGames = async () => {
    try {
      const response = await axios.get("http://localhost:5000/api/games");
      setGames(response.data.games);
    } catch (error) {
      console.error("Error fetching games:", error);
    }
  };

  const handleGameClick = (gameId) => {
    // Load the selected game
    console.log("Loading game with ID:", gameId);
    // Add your logic to load the game component based on the gameId
  };

  //   const parseJsonConfig = (confData) => {
  //     try {
  //       let rawData = confData;

  //       // Check if confData is already an object
  //       if (typeof confData === "object") {
  //         return rawData;
  //       }

  //       // Check if confData is a string
  //       if (typeof rawData !== "string") {
  //         rawData = JSON.stringify(rawData);
  //       }

  //       return JSON.parse(rawData);
  //     } catch (error) {
  //       console.error("Error parsing JSON config:", error);
  //       return {};
  //     }
  //   };

  const formatCurrency = (amount) => {
    return amount.toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
    });
  };

  return (
    <div className="pi-lotto-dashboard">
      <h2>Pi-Lotto Games</h2>
      <div className="game-list">
        {games.map((game) => {
          const drawSchedule = JSON.parse(game.game_config.draw_schedule);

          return (
            <div
              key={game.id}
              className="game-card"
              onClick={() => handleGameClick(game.id)}
            >
              <img
                src={game.game_config.game_image}
                alt={game.name}
                className="game-image"
              />
              <div className="game-info">
                <h3>{game.name}</h3>
                <div className="game-details">
                  <p>Entry Fee: {formatCurrency(game.entry_fee)}</p>
                  <p>Current Pool: {formatCurrency(game.pool_amount)}</p>
                </div>
                <div className="draw-schedule">
                  <p>
                    Draw: {drawSchedule.day} at{" "}
                    <strong>{drawSchedule.time}</strong>
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
