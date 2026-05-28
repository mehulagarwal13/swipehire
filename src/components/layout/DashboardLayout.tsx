"use client";

import Sidebar from "./Sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-black text-white overflow-hidden">

      {/* Background Glow */}
      <div className="fixed inset-0 -z-10">

        <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-purple-500/20 blur-[120px]" />

        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-blue-500/20 blur-[120px]" />

      </div>

      <Sidebar />

      <main className="flex-1 p-8">
        {children}
      </main>

    </div>
  );
}