"use client";

import { useEffect } from "react";

export default function DashboardPage() {

  useEffect(() => {
    const token =
      localStorage.getItem("token");

    if (!token) {
      window.location.href = "/login";
    }
  }, []);

  return (
    <div className="min-h-screen bg-black text-white p-10">
      <h1 className="text-4xl font-bold">
        Welcome to SwipeHire Dashboard 🚀
      </h1>
    </div>
  );
}