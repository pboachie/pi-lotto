// UserTickets.jsx
import React, { useEffect, useState } from 'react';
import $ from 'jquery';
import '../../node_modules/datatables.net-dt/css/dataTables.dataTables.css';
import { makeApiRequest } from '../utils/api';
import '../css/UserTickets.css'; // Ensure this CSS file is imported

const UserTickets = () => {
  const [tickets, setTickets] = useState([]);

  useEffect(() => {
    const fetchTickets = async () => {
      try {
        const response = await makeApiRequest('get', 'http://localhost:5000/users/user-tickets');
        if (response.status === 200) {
          setTickets(response.data.tickets);
          $('#ticketsTable').DataTable();
        } else {
          alert(response.data.error);
        }
      } catch (error) {
        console.error('Error fetching tickets:', error);
      }
    };

    fetchTickets();
  }, []);

  return (
    <div className="user-tickets">
      <h2>Your Tickets</h2>
      <table id="ticketsTable" className="display">
        <thead>
          <tr>
            <th data-label="Game Name">Game Name</th>
            <th data-label="Numbers Played">Numbers Played</th>
            <th data-label="Power Number">Power Number</th>
            <th data-label="Date Purchased">Date Purchased</th>
            <th data-label="Won">Won</th>
            <th data-label="Prize Claimed">Prize Claimed</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map(ticket => (
            <tr key={ticket.ticket_id}>
              <td data-label="Game Name">{ticket.game_name}</td>
              <td data-label="Numbers Played">{ticket.numbers_played}</td>
              <td data-label="Power Number">{ticket.power_number}</td>
              <td data-label="Date Purchased">{new Date(ticket.date_purchased).toLocaleString()}</td>
              <td data-label="Won">{ticket.won ? 'Yes' : 'No'}</td>
              <td data-label="Prize Claimed">{ticket.prize_claimed ? 'Yes' : 'No'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default UserTickets;
