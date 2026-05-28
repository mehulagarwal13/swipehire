"use client";

import {
  Briefcase,
  Sparkles,
  User2,
} from "lucide-react";

import DashboardLayout from
  "@/components/layout/DashboardLayout";

export default function DashboardPage() {

  return (
    <DashboardLayout>

      <div className="space-y-8">

        {/* Hero Section */}
        <div className="bg-white/5 border border-white/10 backdrop-blur-xl rounded-3xl p-8">

          <div className="flex items-center justify-between">

            <div>

              <p className="text-zinc-400 mb-2">
                Welcome back
              </p>

              <h1 className="text-5xl font-bold">
                Shagun 🚀
              </h1>

              <p className="text-zinc-400 mt-4 max-w-xl">
                Your AI-powered career journey
                is evolving. Let’s find your
                next opportunity.
              </p>

            </div>

            <div className="w-24 h-24 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-3xl font-bold">
              S
            </div>

          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          <div className="bg-white/5 border border-white/10 backdrop-blur-xl rounded-3xl p-6 hover:scale-[1.02] transition-all">

            <Sparkles className="mb-4 text-purple-400" />

            <h2 className="text-3xl font-bold">
              92%
            </h2>

            <p className="text-zinc-400">
              AI Match Score
            </p>

          </div>

          <div className="bg-white/5 border border-white/10 backdrop-blur-xl rounded-3xl p-6 hover:scale-[1.02] transition-all">

            <Briefcase className="mb-4 text-blue-400" />

            <h2 className="text-3xl font-bold">
              12
            </h2>

            <p className="text-zinc-400">
              Applied Jobs
            </p>

          </div>

          <div className="bg-white/5 border border-white/10 backdrop-blur-xl rounded-3xl p-6 hover:scale-[1.02] transition-all">

            <User2 className="mb-4 text-pink-400" />

            <h2 className="text-3xl font-bold">
              85%
            </h2>

            <p className="text-zinc-400">
              Profile Completion
            </p>

          </div>

        </div>

      </div>

    </DashboardLayout>
  );
}