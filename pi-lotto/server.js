const express = require('express');
const http = require('http');
const path = require('path');
const WebSocket = require('ws');

const app = express();
const PORT = process.env.PORT || 3000; // Define the port

// Serve static files from the build folder
app.use(express.static(path.join(__dirname, 'build')));

// Create an HTTP server instance using Express app
const server = http.createServer(app);

// Create a WebSocket server instance using the HTTP server
const wss = new WebSocket.Server({ server });

// WebSocket connection handler
wss.on('connection', (ws) => {
  console.log('WebSocket connection established.');

  // WebSocket message handler
  ws.on('message', (message) => {
    console.log('Received message:', message);
    // Handle incoming messages here
    // Example: echo back the message
    ws.send(`Echo: ${message}`);
  });

  // WebSocket close handler
  ws.on('close', () => {
    console.log('WebSocket connection closed.');
  });
});

// Serve the React app for any route
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'build', 'index.html'));
});

// Start the HTTP server
server.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
