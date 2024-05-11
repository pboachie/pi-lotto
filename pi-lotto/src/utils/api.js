// utils/api.js
import axios from 'axios';
import { refreshAccessToken } from './auth';

export const makeApiRequest = async (method, url, data = null, config = {}) => {
  const accessToken = localStorage.getItem('@pi-lotto:access_token');

  // Check if the access token exists and is not expired
  if (isAccessTokenExpired(accessToken)) {
    const newAccessToken = await refreshAccessToken();
    if (!newAccessToken) {
        alert('Your session has expired. Please sign in again.');
        window.location.href = '/';
      return;
    }
    config.headers = {
      ...config.headers,
      Authorization: `Bearer ${newAccessToken}`,
    };
  } else {
    config.headers = {
      ...config.headers,
      Authorization: `Bearer ${accessToken}`,
    };
  }

  try {
    let response;
    switch (method.toLowerCase()) {
      case 'get':
        response = await axios.get(url, config);
        break;
      case 'post':
        response = await axios.post(url, data, config);
        break;
      case 'put':
        response = await axios.put(url, data, config);
        break;
      case 'delete':
        response = await axios.delete(url, config);
        break;
      default:
        throw new Error(`Unsupported HTTP method: ${method}`);
    }
    return response;
  } catch (error) {
    console.error('API request error:', error);

    // Remove the access token from the local storage
    localStorage.removeItem('@pi-lotto:access_token');

    // Redirect to the sign-in page
    window.location.href = '/';
    return null;
  }
};

// Helper function to check if the access token has expired
const isAccessTokenExpired = (accessToken) => {
  if (!accessToken) {
    return true;
  }

  const decodedToken = JSON.parse(atob(accessToken.split('.')[1]));
  const currentTime = Date.now() / 1000;
  return decodedToken.exp < currentTime;
};