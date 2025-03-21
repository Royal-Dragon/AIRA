import React, { useState } from "react";
import { registerUser } from "../api/auth";
import { Link, useNavigate } from "react-router-dom";
import Logo from '../source/white.png'

const Register = () => {
  const [formData, setFormData] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const response = await registerUser(formData);
      if (response.error) {
        setError(response.error); // Display backend error (e.g., "User already exists")
      } else {
        navigate("/login"); // Redirect to login on success
      }
    } catch (err) {
      setError("An error occurred. Please try again."); // Network or fetch error
    }
  };

  return (
    <div className="flex min-h-screen bg-bg-color font-urbanist">
      <div className="flex items-center justify-center w-full">
        <div className="bg-gray-800 p-8 rounded-lg shadow-lg w-96 animate-fade-in">
          {/* Title Section */}
          <div className="text-center mb-6">
            <img src={Logo} alt="Logo" width={50} className="block mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-white mt-4">REGISTER</h2>
            <p className="text-gray-400">Create your account</p>
          </div>

          {/* Register Form */}
          <form onSubmit={handleSubmit}>
            {/* Username Input */}
            <div className="mb-4">
              <div className="relative">
                <i className="fas fa-user absolute left-3 top-3 text-gray-400"></i>
                <input
                  name="username"
                  placeholder="Username"
                  value={formData.username}
                  onChange={handleChange}
                  className="w-full pl-10 pr-3 py-2 bg-gray-700 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            </div>

            {/* Email Input */}
            <div className="mb-4">
              <div className="relative">
                <i className="fas fa-envelope absolute left-3 top-3 text-gray-400"></i>
                <input
                  name="email"
                  type="email"
                  placeholder="Email"
                  value={formData.email}
                  onChange={handleChange}
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
                  name="password"
                  type="password"
                  placeholder="Password"
                  value={formData.password}
                  onChange={handleChange}
                  className="w-full pl-10 pr-3 py-2 bg-gray-700 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="w-full bg-gradient-to-r from-blue-start to-blue-end text-white py-2 rounded-md hover:opacity-90 transition-opacity border-1 cursor-pointer"
            >
              REGISTER NOW
            </button>
          </form>

          {/* Error Message */}
          {error && <p className="text-red-500 text-center mt-4">{error}</p>}

          {/* Login Link */}
          <p className="text-center text-gray-400 mt-4">
            Already have an account?{" "}
            <Link to="/login" className="text-blue-400 hover:underline">
              Login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;