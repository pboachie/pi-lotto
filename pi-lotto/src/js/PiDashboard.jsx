// PiDashboard.jsx
import React, { useEffect, useState, useRef, useCallback } from "react";
import PiLottoDashboard from "./PiLottoDashboard";
import PiAuthentication from "./PiAuthentication";
import SideMenu from "./SideMenu";
import PiDeposit from "./PiDeposit";
import PiWithdraw from "./PiWithdraw";
import PurchaseModal from './PurchaseModal';
import { makeApiRequest } from '../utils/api';
import "../css/PiDashboard.css";
import { FaBars, FaUser } from "react-icons/fa";

function PiLotto() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [userBalance, setUserBalance] = useState(parseFloat(0.0));
  const [currentTime, setCurrentTime] = useState(new Date());
  const [selectedGame, setSelectedGame] = useState(null);
  const [isSideMenuOpen, setIsSideMenuOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isDepositVisible, setIsDepositVisible] = useState(false);
  const [isWithdrawVisible, setIsWithdrawVisible] = useState(false);
  const [isLogoutModalVisible, setIsLogoutModalVisible] = useState(false);
  const [isPurchaseModalVisible, setIsPurchaseModalVisible] = useState(false);
  const [gameTypes, setGameTypes] = useState([]);


  const userIconRef = useRef(null);

  useEffect(() => {
    const Pi = window.Pi;
    Pi.init({ version: "2.0", sandbox: process.env.NODE_ENV !== "production" });
  }, []);

  const updateUserBalance = useCallback(
    (newBalance) => {
      const balanceElement = document.querySelector(
        ".user-info .user-details span:last-child"
      );
      const prevBalance = userBalance;

      if (newBalance > prevBalance) {
        balanceElement.classList.add("balance-increase");
      } else if (newBalance < prevBalance) {
        balanceElement.classList.add("balance-decrease");
      }

      setTimeout(() => {
        balanceElement.classList.remove("balance-increase", "balance-decrease");
      }, 500);

      setUserBalance(newBalance);
    },
    [userBalance]
  );

  const fetchUserBalance = useCallback(async () => {
    try {
      const response = await makeApiRequest('get',
        "http://localhost:5000/api/user-balance"
      );

      const status = response.status === 200;

      if (!status) {
        setUserBalance(parseFloat(0.0));
        alert(response.data.error);
        return;
      }

      updateUserBalance(parseFloat(response.data.balance));
    } catch (error) {
      alert("Server currently under maintenance. Please try again later.");
    }
  }, [updateUserBalance]);

  const fetchGameTypes = useCallback(async () => {
    try {
      const response = await makeApiRequest('get', "http://localhost:5000/game-types");
      setGameTypes(response.data);
    } catch (error) {
      console.error("Error fetching game types:", error);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated && user) {
      fetchUserBalance();
      fetchGameTypes();
    }
  }, [isAuthenticated, user, fetchUserBalance, fetchGameTypes]);



  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => {
      clearInterval(timer);
    };
  }, []);

  const handleAuthentication = (authenticated, userInfo) => {
    setIsAuthenticated(authenticated);
    setUser(userInfo);
  };

  const handleCloseComponents = () => {
    setIsDepositVisible(false);
    setIsWithdrawVisible(false);
    setIsPurchaseModalVisible(false);
    setSelectedGame(null);
  };

  const handleGameClick = (game) => {
    setSelectedGame(game);
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
    }, 200);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userIconRef.current && !userIconRef.current.contains(event.target)) {
        setIsUserMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const toggleSideMenu = () => {
    setIsSideMenuOpen(!isSideMenuOpen);
  };

  const toggleUserMenu = () => {
    setIsUserMenuOpen(!isUserMenuOpen);
  };

  const handleDeposit = () => {
    // Close other components
    handleCloseComponents();

    setIsDepositVisible(true);
  };

  const handleWithdraw = () => {

    // Close other components
    handleCloseComponents();

    setIsWithdrawVisible(true);
  };

  const handleLogout = () => {
    setIsLogoutModalVisible(true);
  };

  const handleConfirmLogout = () => {
    // Clear the access token from the local storage
    localStorage.removeItem("@pi-lotto:access_token");

    // Reset the user state
    setIsAuthenticated(false);
    setUser(null);
    setUserBalance(parseFloat(0.0));

    // Close the user menu
    setIsUserMenuOpen(false);

    // Close the side menu
    setIsSideMenuOpen(false);

    // Reset the selected game
    setSelectedGame(null);

    // Reset the visibility of the components
    setIsDepositVisible(false);
    setIsWithdrawVisible(false);

    // Close the logout modal
    setIsLogoutModalVisible(false);
  };

  const handleCancelLogout = () => {
    setIsLogoutModalVisible(false);
  };

  const renderMainContent = () => {
    if (!isAuthenticated) {
      return (
        <PiAuthentication
          onAuthentication={handleAuthentication}
          isAuthenticated={isAuthenticated}
          onBalanceUpdate={fetchUserBalance}
        />
      );
    }

    if (isLoading) {
      return <div className="loading">Loading...</div>;
    }

    if (selectedGame === "pilotto") {
      return <PiLottoDashboard />;
    }

    if (isDepositVisible) {
      return <PiDeposit onClose={() => setIsDepositVisible(false)} isAuthenticated={isAuthenticated} userBalance={userBalance} updateUserBalance={updateUserBalance} />;

    }

    if (isWithdrawVisible) {
      return <PiWithdraw onClose={() => setIsWithdrawVisible(false)} isAuthenticated={isAuthenticated} userBalance={userBalance} updateUserBalance={updateUserBalance} />;
    }

    return (
      <div className="home-page">
        <h2>Current Local Time:</h2>
        <p className="current-time">{currentTime.toLocaleString()}</p>
      </div>
    );
  };

  return (
    <div className="pi-lotto">
      <header className="top-bar">
        <button className="menu-btn" onClick={toggleSideMenu}>
          <FaBars />
        </button>
        <h1>Uni Pi Games</h1>
        {isAuthenticated && (
          <div className="user-info">
            <div className="user-details">
              <span>Welcome, {user.username}</span>
              <span>
                Balance: {userBalance}{" "}
                {process.env.NODE_ENV === "production" ? "π" : "Test-π"}
              </span>
            </div>
            <div
              className={`user-icon ${isUserMenuOpen ? "active" : ""}`}
              onClick={toggleUserMenu}
              ref={userIconRef}
            >
              <FaUser />
              {isUserMenuOpen && (
                <div className="user-menu">
                  <button onClick={handleDeposit}>Deposit</button>
                  <button onClick={handleWithdraw}>Withdraw</button>
                  <button onClick={handleLogout}>Logout</button>
                </div>
              )}
            </div>
          </div>
        )}
      </header>
      {isAuthenticated && (
        <SideMenu
          isOpen={isSideMenuOpen}
          onGameClick={handleGameClick}
          onClose={toggleSideMenu}
          onCloseComponents={handleCloseComponents}
          gameTypes={gameTypes}
        />
      )}

      {isLogoutModalVisible && (
        <div className="logout-modal">
          <div className="logout-modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Confirm Logout</h3>
            <p>Are you sure you want to logout?</p>
            <div className="logout-modal-buttons">
              <button onClick={handleConfirmLogout}>OK</button>
              <button onClick={handleCancelLogout}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {isPurchaseModalVisible && (
        <PurchaseModal
          numberSets={null}
          ticketNumber={0}
          ticketPrice={0}
          baseFee={0}
          serviceFee={0}
          onClose={() => setIsPurchaseModalVisible(false)}
            />
      )}
      <div className="main-content">{renderMainContent()}</div>
    </div>
  );
}

export default PiLotto;
