"use client";

import { useState } from "react";

export default function LoginPage() {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleLogin = async (
    e: React.FormEvent<HTMLFormElement>
  ) => {
    e.preventDefault();

    try {
      const response = await fetch(
        "http://127.0.0.1:5000/login",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(formData),
        }
      );

      const data = await response.json();

      alert(data.message);

localStorage.setItem(
  "token",
  data.token
);

window.location.href = "/dashboard";

      // Save token later
      // localStorage.setItem("token", data.token);

    } catch (error) {
      console.log(error);

      alert("Login failed");
    }
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center text-white">
      <form
        onSubmit={handleLogin}
        className="bg-zinc-900 p-8 rounded-2xl w-[400px] space-y-4"
      >
        <h1 className="text-3xl font-bold">
          SwipeHire Login
        </h1>

        <input
          type="email"
          name="email"
          placeholder="Email"
          onChange={handleChange}
          className="w-full p-3 rounded-lg bg-zinc-800"
        />

        <input
          type="password"
          name="password"
          placeholder="Password"
          onChange={handleChange}
          className="w-full p-3 rounded-lg bg-zinc-800"
        />

        <button
          type="submit"
          className="w-full bg-white text-black py-3 rounded-lg font-semibold"
        >
          Login
        </button>
      </form>
    </div>
  );
}