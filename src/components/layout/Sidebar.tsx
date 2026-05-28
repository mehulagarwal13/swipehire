"use client";

import {
  LayoutDashboard,
  User,
  FileText,
  Briefcase,
  Settings,
} from "lucide-react";

export default function Sidebar() {

  const menuItems = [
    {
      icon: LayoutDashboard,
      label: "Dashboard",
    },
    {
      icon: User,
      label: "Profile",
    },
    {
      icon: FileText,
      label: "Resume",
    },
    {
      icon: Briefcase,
      label: "Jobs",
    },
    {
      icon: Settings,
      label: "Settings",
    },
  ];

  return (
    <div className="w-[260px] min-h-screen border-r border-white/10 bg-white/5 backdrop-blur-xl p-6">

      <h1 className="text-3xl font-bold text-white mb-10">
        SwipeHire
      </h1>

      <div className="space-y-3">

        {menuItems.map((item, index) => {

          const Icon = item.icon;

          return (
            <button
              key={index}
              className="w-full flex items-center gap-4 p-4 rounded-2xl text-zinc-300 hover:bg-white/10 hover:text-white transition-all duration-300"
            >
              <Icon size={22} />

              <span className="font-medium">
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}