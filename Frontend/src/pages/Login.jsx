import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import useAuthStore from "../store/authStore";
import { loginUser } from "../api/auth";
import Logo from "../source/white.png";
import { useEffect } from "react";

const Login = () => {
  const [email, setEmail] = useState("");
  // if (!user) return <p>Loading...</p>;
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuthStore();

  if (isAuthenticated) {
    useEffect(() => {
      navigate("/dashboard", { replace: true }); // Navigates after component mounts
    }, [navigate]);
    return null;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const response = await loginUser({ email, password });
      const res_error = response.error;
      if (res_error) {
        setError(res_error);
      } else {
        login(response.user, response.access_token, response.refresh_token);
        if (response.user.is_new_user) {
          // navigate("/dashboard", { state: { showOnboarding: true } });
          navigate("/dashboard");
        } else {
          navigate("/dashboard");
        }
      }
    } catch (err) {
      setError("An error occurred. Please try again.");
    }
  };

  return (
    <div className="flex min-h-screen bg-bg-color font-urbanist">
      <div className="flex items-center justify-center w-full">
        <div className="bg-gray-800 p-8 rounded-lg shadow-lg w-96 animate-fade-in">
          {/* Title Section */}
          <div className="text-center mb-6">
            <img
              src={Logo}
              alt="Logo"
              width={50}
              className="block mx-auto mb-4"
            />
            <h2 className="text-2xl font-bold text-white mt-4">LOGIN</h2>
            <p className="text-gray-400">Welcome back 👋</p>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit}>
            {/* Email Input */}
            <div className="mb-4">
              <div className="relative">
                <i className="fas fa-user absolute left-3 top-3 text-gray-400"></i>
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 bg-gray-700 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            </div>

            {/* Password Input */}
            <div className="mb-6">
              <div className="relative">
                <i className="fas fa-lock absolute left-3 top-3 text-gray-400"></i>
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 bg-gray-700 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="w-full bg-gradient-to-r from-blue-start to-blue-end text-white py-2 rounded-md hover:opacity-90 transition-opacity cursor-pointer border-1"
            >
              LOGIN NOW
            </button>
          </form>

          {/* Error Message */}
          {error && <p className="text-red-500 text-center mt-4">{error}</p>}

          {/* Register Link */}
          <p className="text-center text-gray-400 mt-4 mb-5">
            Don't have an account?{" "}
            <Link to="/register" className="text-blue-400 hover:underline">
              Register
            </Link>
          </p>

          {/* Social Login Separator */}
          <div className="text-center text-gray-400 mb-4">
            <hr className="border-gray-600" />
            <span className="relative top-[-10px] bg-gray-800 px-2">
              Login with Others
            </span>
          </div>

          {/* Social Login Buttons */}
          <div className="space-y-4">
            <button
              className="w-full flex items-center justify-center border border-white text-white py-2 rounded-md hover:bg-gray-700 transition-colors cursor-pointer"
              onClick={() =>
                (window.location.href =
                  "http://localhost:5000/api/auth/google/login")
              }
            >
              <i className="fab fa-google mr-2"></i> Login with Google
            </button>
            <button
              className="w-full flex items-center justify-center border border-white text-white py-2 rounded-md hover:bg-gray-700 transition-colors cursor-pointer"
              onClick={() =>
                (window.location.href =
                  "http://localhost:5000/api/auth/facebook")
              }
            >
              <i className="fab fa-facebook mr-2"></i> Login with Facebook
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
