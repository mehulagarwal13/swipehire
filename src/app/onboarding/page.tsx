"use client";

import { useState } from "react";

export default function OnboardingPage() {

  const [formData, setFormData] =
    useState({
      college: "",
      skills: "",
      role: "",
      location: "",
      bio: "",
      experience: "",
    });

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement |
      HTMLTextAreaElement
    >
  ) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>
  ) => {
    e.preventDefault();

    const token =
      localStorage.getItem("token");

    const response = await fetch(
      "http://127.0.0.1:5000/onboarding",
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",

          Authorization: `Bearer ${token}`,
        },

        body: JSON.stringify(formData),
      }
    );

    const data = await response.json();

    alert(data.message);
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-10">

      <form
        onSubmit={handleSubmit}
        className="bg-zinc-900 p-8 rounded-2xl w-full max-w-2xl space-y-4"
      >
        <h1 className="text-4xl font-bold">
          Candidate Onboarding
        </h1>

        <input
          type="text"
          name="college"
          placeholder="College"
          onChange={handleChange}
          className="w-full p-3 rounded-lg bg-zinc-800"
        />

        <input
          type="text"
          name="skills"
          placeholder="Skills (React, Node, Python)"
          onChange={handleChange}
          className="w-full p-3 rounded-lg bg-zinc-800"
        />

        <input
          type="text"
          name="role"
          placeholder="Preferred Role"
          onChange={handleChange}
          className="w-full p-3 rounded-lg bg-zinc-800"
        />

        <input
          type="text"
          name="location"
          placeholder="Location"
          onChange={handleChange}
          className="w-full p-3 rounded-lg bg-zinc-800"
        />

        <input
          type="text"
          name="experience"
          placeholder="Experience"
          onChange={handleChange}
          className="w-full p-3 rounded-lg bg-zinc-800"
        />

        <textarea
          name="bio"
          placeholder="Tell us about yourself"
          onChange={handleChange}
          className="w-full p-3 rounded-lg bg-zinc-800 h-32"
        />

        <button
          type="submit"
          className="w-full bg-white text-black py-3 rounded-lg font-semibold"
        >
          Save Profile
        </button>
      </form>
    </div>
  );
}