import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';

const AuthCallback = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      console.log('User already authenticated, redirecting to dashboard');
      navigate('/dashboard', { replace: true });
      return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    if (code) {
      fetch('http://localhost:5000/api/auth/exchange_code', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code }),
      })
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          console.log('Exchange Code Response:', data);
          if (data.access_token && data.refresh_token) {
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
            login(data.user, data.access_token, data.refresh_token);
            console.log('User:', data.user);
            navigate('/dashboard', { replace: true });
          } else {
            console.error('Error: No tokens received in response');
            navigate('/login', { replace: true });
          }
        })
        .catch(error => {
          console.error('Error exchanging code:', error);
          navigate('/login', { replace: true });
        });
    } else {
      console.error('No code found in URL');
      navigate('/login', { replace: true });
    }
  }, [navigate, login, isAuthenticated]);

  return <div>Loading...</div>;
};

export default AuthCallback;