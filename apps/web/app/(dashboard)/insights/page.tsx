"use client";

import { useQuery } from "@tanstack/react-query";
import { applicationsApi, profileApi, type Application } from "@/lib/api";
import { TrendingUp, CheckCircle2, XCircle, Clock, Award, Target, Briefcase } from "lucide-react";
import { MatchBadge } from "@/components/swipe/MatchBadge";

// ─── Derived analytics ────────────────────────────────────────────────────────

function deriveStats(apps: Application[]) {
  const total = apps.length;
  const byStatus = apps.reduce<Record<string, number>>((acc, a) => {
    acc[a.status] = (acc[a.status] ?? 0) + 1;
    return acc;
  }, {});

  const active   = apps.filter(a => !["rejected","withdrawn","offer_accepted","offer_rejected"].includes(a.status)).length;
  const offers   = (byStatus["offer_extended"] ?? 0) + (byStatus["offer_accepted"] ?? 0);
  const rejected = byStatus["rejected"] ?? 0;
  const responseRate = total > 0 ? Math.round(((total - rejected) / total) * 100) : 0;

  // Weekly application trend (last 8 weeks)
  const now = Date.now();
  const weeks: { label: string; count: number }[] = Array.from({ length: 8 }, (_, i) => {
    const weekStart = now - (7 - i) * 7 * 24 * 60 * 60 * 1000;
    const weekEnd   = weekStart + 7 * 24 * 60 * 60 * 1000;
    const count = apps.filter(a => {
      const t = new Date(a.applied_at).getTime();
      return t >= weekStart && t < weekEnd;
    }).length;
    const d = new Date(weekStart);
    return { label: `${d.getDate()}/${d.getMonth() + 1}`, count };
  });

  return { total, active, offers, rejected, responseRate, byStatus, weeks };
}

// ─── Mini bar chart ───────────────────────────────────────────────────────────

function TrendChart({ weeks }: { weeks: { label: string; count: number }[] }) {
  const max = Math.max(...weeks.map(w => w.count), 1);
  return (
    <div className="flex items-end gap-2 h-24">
      {weeks.map((w, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1">
          <div
            className="w-full bg-brand-400 rounded-t-md transition-all duration-500"
            style={{ height: `${Math.max((w.count / max) * 88, w.count > 0 ? 6 : 2)}px` }}
          />
          <span className="text-xs text-gray-400 rotate-[-45deg] origin-top-left translate-x-1">
            {w.label}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Funnel ───────────────────────────────────────────────────────────────────

const FUNNEL_STAGES = [
  { key: "applied",             label: "Applied",    color: "bg-blue-400" },
  { key: "screening",           label: "Screening",  color: "bg-yellow-400" },
  { key: "interview_scheduled", label: "Interview",  color: "bg-purple-400" },
  { key: "offer_extended",      label: "Offer",      color: "bg-green-400" },
  { key: "offer_accepted",      label: "Accepted",   color: "bg-brand-500" },
];

function Funnel({ byStatus, total }: { byStatus: Record<string, number>; total: number }) {
  if (total === 0) return <p className="text-gray-400 text-sm">No applications yet</p>;

  return (
    <div className="space-y-2">
      {FUNNEL_STAGES.map(stage => {
        const count = byStatus[stage.key] ?? 0;
        const pct   = total > 0 ? Math.round((count / total) * 100) : 0;
        return (
          <div key={stage.key}>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>{stage.label}</span>
              <span className="font-semibold">{count} ({pct}%)</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div
                className={`${stage.color} h-2 rounded-full transition-all duration-700`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InsightsPage() {
  const { data: apps = [], isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: applicationsApi.list,
  });

  const { data: profile } = useQuery({
    queryKey: ["profile"],
    queryFn: profileApi.get,
  });

  const { data: scoreData } = useQuery({
    queryKey: ["profile-score"],
    queryFn: profileApi.getScore,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
      </div>
    );
  }

  const stats = deriveStats(apps);

  const statCards = [
    { label: "Total Applied",   value: stats.total,        icon: Briefcase,  color: "text-blue-600",   bg: "bg-blue-50" },
    { label: "Active",          value: stats.active,       icon: Clock,      color: "text-yellow-600", bg: "bg-yellow-50" },
    { label: "Offers",          value: stats.offers,       icon: Award,      color: "text-green-600",  bg: "bg-green-50" },
    { label: "Response Rate",   value: `${stats.responseRate}%`, icon: TrendingUp, color: "text-brand-600", bg: "bg-brand-50" },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Insights</h1>
        <p className="text-gray-500 text-sm mt-1">Your job search analytics at a glance</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {statCards.map(card => (
          <div key={card.label} className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
            <div className={`w-10 h-10 ${card.bg} rounded-xl flex items-center justify-center mb-3`}>
              <card.icon className={`w-5 h-5 ${card.color}`} />
            </div>
            <p className="text-2xl font-bold text-gray-900">{card.value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{card.label}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mb-6">
        {/* Application trend */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
          <h2 className="font-semibold text-gray-900 mb-5">Weekly Applications</h2>
          <TrendChart weeks={stats.weeks} />
        </div>

        {/* Conversion funnel */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
          <h2 className="font-semibold text-gray-900 mb-5">Application Funnel</h2>
          <Funnel byStatus={stats.byStatus} total={stats.total} />
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Profile score */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
          <h2 className="font-semibold text-gray-900 mb-4">Profile Strength</h2>
          {profile && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-3xl font-bold text-gray-900">{scoreData?.score ?? profile.profile_score}%</span>
                <MatchBadge score={scoreData?.score ?? profile.profile_score} size="lg" showLabel={false} />
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3">
                <div
                  className="bg-gradient-to-r from-brand-400 to-brand-600 h-3 rounded-full transition-all duration-700"
                  style={{ width: `${scoreData?.score ?? profile.profile_score}%` }}
                />
              </div>
              {scoreData?.missing && scoreData.missing.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-2">To improve your score:</p>
                  <ul className="space-y-1.5">
                    {scoreData.missing.slice(0, 3).map(m => (
                      <li key={m} className="text-xs text-amber-700 flex items-center gap-1.5">
                        <Target className="w-3 h-3 flex-shrink-0" />
                        {m}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="pt-2 border-t border-gray-100">
                <p className="text-xs text-gray-500">
                  <span className="font-medium">{profile.skills.length}</span> skills ·{" "}
                  <span className="font-medium">{profile.experience_years}</span> yrs exp ·{" "}
                  <span className="font-medium">{profile.preferred_locations.join(", ") || "—"}</span>
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Recent applications */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
          <h2 className="font-semibold text-gray-900 mb-4">Recent Activity</h2>
          {apps.length === 0 ? (
            <p className="text-gray-400 text-sm">No applications yet. Start swiping!</p>
          ) : (
            <ul className="space-y-3">
              {apps.slice(0, 6).map(app => (
                <li key={app.id} className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-500 flex-shrink-0">
                    {app.company[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{app.title}</p>
                    <p className="text-xs text-gray-400">{app.company}</p>
                  </div>
                  <StatusDot status={app.status} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string }> = {
    applied:              { color: "bg-blue-400",   label: "Applied" },
    screening:            { color: "bg-yellow-400", label: "Screening" },
    interview_scheduled:  { color: "bg-purple-400", label: "Interview" },
    offer_extended:       { color: "bg-green-400",  label: "Offer" },
    offer_accepted:       { color: "bg-brand-500",  label: "Accepted" },
    rejected:             { color: "bg-red-400",    label: "Rejected" },
    withdrawn:            { color: "bg-gray-300",   label: "Withdrawn" },
  };
  const s = map[status] ?? { color: "bg-gray-300", label: status };
  return (
    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${s.color}`} title={s.label} />
  );
}
