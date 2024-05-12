// utils/auth.js
import axios from 'axios';

export const refreshAccessToken = async () => {
  try {
    const refreshToken = localStorage.getItem('@pi-lotto:refresh_token');
    const response = await axios.post('https://api.unipigames.com/refresh-token', { refresh_token: refreshToken });
    const newAccessToken = response.data.access_token;
    localStorage.setItem('@pi-lotto:access_token', newAccessToken);
    return newAccessToken;
  } catch (error) {
    console.error('Failed to refresh access token:', error);
    // Remove the access token from the local storage
    localStorage.removeItem('@pi-lotto:access_token');

    // Redirect to the sign-in page
    window.location.href = '/';
    return null;
  }
};

