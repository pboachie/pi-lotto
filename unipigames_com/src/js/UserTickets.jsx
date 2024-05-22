import React, { useEffect, useState } from 'react';
import { makeApiRequest } from '../utils/api';
import '../css/UserTickets.css';

const darkTextClass = "dark:text-zinc-400";
const darkBgClass = "dark:bg-zinc-700";
const textZinc600Dark = "text-zinc-600 " + darkTextClass;

const UserTickets = () => {
  const [tickets, setTickets] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedTicket, setExpandedTicket] = useState(null);

  useEffect(() => {
    const fetchTickets = async () => {
      try {
        const response = await makeApiRequest('get', 'http://localhost:5000/users/user-tickets');
        if (response.status === 200) {
          setTickets(response.data.tickets);
        } else {
          alert(response.data.error);
        }
      } catch (error) {
        console.error('Error fetching tickets:', error);
      }
    };

    fetchTickets();
  }, []);

  const filteredTickets = tickets.filter(ticket =>
    ticket.game_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const groupedTickets = filteredTickets.reduce((acc, ticket) => {
    if (!acc[ticket.game_name]) {
      acc[ticket.game_name] = [];
    }
    acc[ticket.game_name].push(ticket);
    return acc;
  }, {});

  const toggleTicketDetails = (ticketId) => {
    setExpandedTicket(expandedTicket === ticketId ? null : ticketId);
  };

  return (
    <div className="user-tickets-container">
      <div className="max-w-md mx-auto bg-zinc-100 dark:bg-zinc-800 rounded-lg shadow-lg h-screen overflow-y-auto">
        <Header />
        <SearchInput searchTerm={searchTerm} setSearchTerm={setSearchTerm} />
        <TicketList groupedTickets={groupedTickets} toggleTicketDetails={toggleTicketDetails} expandedTicket={expandedTicket} />
        <Footer />
      </div>
    </div>
  );
};

const Header = () => (
  <div className={`bg-zinc-200 ${darkBgClass} p-4 flex items-center justify-between`}>
    <span className="text-lg font-semibold text-zinc-800 dark:text-zinc-200">Your Tickets</span>
  </div>
);

const SearchInput = ({ searchTerm, setSearchTerm }) => (
  <div className="p-4">
    <div className="relative mb-4">
      <input
        type="text"
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        placeholder="Search"
        className="w-full p-2 pl-10 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-700 dark:text-zinc-200 dark:placeholder-zinc-400"
      />
      <svg className={`absolute left-3 top-3 w-5 h-5 ${textZinc600Dark}`} fill="currentColor" viewBox="0 0 24 24">
        <path d="M10 2a8 8 0 105.293 14.707l4.707 4.707a1 1 0 001.414-1.414l-4.707-4.707A8 8 0 0010 2zm0 2a6 6 0 110 12A6 6 0 0110 4z" />
      </svg>
    </div>
  </div>
);

const TicketList = ({ groupedTickets, toggleTicketDetails, expandedTicket }) => (
  <div className="p-4 border-t border-zinc-300 dark:border-zinc-600">
    {Object.keys(groupedTickets).length > 0 ? (
      Object.keys(groupedTickets).map(gameName => (
        <div key={gameName}>
          <h3 className="text-lg font-semibold text-zinc-800 dark:text-zinc-200">{gameName}</h3>
          {groupedTickets[gameName].map(ticket => (
            <div key={ticket.ticket_id} className="ticket-card mb-4 p-4 bg-white dark:bg-zinc-700 rounded-lg shadow" onClick={() => toggleTicketDetails(ticket.ticket_id)}>
              <p className="mt-2"><strong>Numbers Played:</strong> {ticket.numbers_played}</p>
              <p><strong>Won:</strong> {ticket.won ? 'Yes' : 'No'}</p>
              {expandedTicket === ticket.ticket_id && (
                <>
                  <p><strong>Power Number:</strong> {ticket.power_number}</p>
                  <p><strong>Date Purchased:</strong> {new Date(ticket.date_purchased).toLocaleString()}</p>
                  <p><strong>Prize Claimed:</strong> {ticket.prize_claimed ? 'Yes' : 'No'}</p>
                </>
              )}
            </div>
          ))}
        </div>
      ))
    ) : (
      <p>No tickets available.</p>
    )}
  </div>
);

const Footer = () => {
  const buttons = [
    { icon: "https://placehold.co/24x24", label: "Home" },
    { icon: "https://placehold.co/24x24", label: "Games" },
    { icon: "https://placehold.co/24x24", label: "Profile" },
    { icon: "https://placehold.co/24x24", label: "Settings" }
  ];

  return (
    <div className={`flex justify-around bg-zinc-200 ${darkBgClass} p-2`}>
      {buttons.map(button => (
        <button key={button.label} className={`flex flex-col items-center ${textZinc600Dark}`}>
          <img src={button.icon} alt={button.label} className="mb-1" />
          <span className="text-xs">{button.label}</span>
        </button>
      ))}
    </div>
  );
};

export default UserTickets;
