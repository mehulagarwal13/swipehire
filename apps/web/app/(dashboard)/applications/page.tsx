"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationsApi, type Application } from "@/lib/api";
import { Building2, MapPin, Calendar, ChevronDown } from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";

const COLUMNS: { key: Application["status"]; label: string; color: string }[] = [
  { key: "applied",              label: "Applied",           color: "bg-blue-100 text-blue-700" },
  { key: "screening",            label: "Screening",         color: "bg-yellow-100 text-yellow-700" },
  { key: "interview_scheduled",  label: "Interview",         color: "bg-purple-100 text-purple-700" },
  { key: "offer_extended",       label: "Offer",             color: "bg-green-100 text-green-700" },
  { key: "rejected",             label: "Rejected",          color: "bg-red-100 text-red-500" },
];

export default function ApplicationsPage() {
  const qc = useQueryClient();

  const { data: apps = [], isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: applicationsApi.list,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      applicationsApi.updateStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      toast.success("Status updated");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
      </div>
    );
  }

  const grouped = COLUMNS.reduce<Record<string, Application[]>>((acc, col) => {
    acc[col.key] = apps.filter((a) => a.status === col.key);
    return acc;
  }, {});

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Applications</h1>
        <p className="text-gray-500 text-sm mt-1">{apps.length} total applications</p>
      </div>

      {/* Kanban board */}
      <div className="flex gap-4 overflow-x-auto pb-4 no-scrollbar">
        {COLUMNS.map((col) => (
          <div key={col.key} className="flex-shrink-0 w-72">
            <div className="flex items-center justify-between mb-3">
              <span className={cn("text-xs font-semibold px-2.5 py-1 rounded-full", col.color)}>
                {col.label}
              </span>
              <span className="text-xs text-gray-400 font-medium">
                {grouped[col.key]?.length ?? 0}
              </span>
            </div>
            <div className="space-y-3">
              {(grouped[col.key] ?? []).map((app) => (
                <ApplicationCard
                  key={app.id}
                  app={app}
                  onStatusChange={(status) => updateMutation.mutate({ id: app.id, status })}
                />
              ))}
              {(grouped[col.key] ?? []).length === 0 && (
                <div className="rounded-2xl border-2 border-dashed border-gray-200 p-4 text-center text-xs text-gray-400">
                  None here
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ApplicationCard({
  app,
  onStatusChange,
}: {
  app: Application;
  onStatusChange: (status: string) => void;
}) {
  const NEXT_STATUS: Record<string, string> = {
    applied:             "screening",
    screening:           "interview_scheduled",
    interview_scheduled: "offer_extended",
    offer_extended:      "offer_accepted",
  };

  const next = NEXT_STATUS[app.status];

  return (
    <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
      <div className="flex items-start gap-3 mb-3">
        <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-sm font-bold text-gray-500 flex-shrink-0">
          {app.company[0]}
        </div>
        <div className="min-w-0">
          <p className="font-semibold text-gray-900 text-sm truncate">{app.title}</p>
          <div className="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
            <Building2 className="w-3 h-3" />
            <span className="truncate">{app.company}</span>
          </div>
        </div>
      </div>

      {app.location && (
        <div className="flex items-center gap-1 text-xs text-gray-400 mb-2">
          <MapPin className="w-3 h-3" />
          {app.location}
        </div>
      )}

      {app.interview_date && (
        <div className="flex items-center gap-1 text-xs text-purple-600 mb-2 font-medium">
          <Calendar className="w-3 h-3" />
          {new Date(app.interview_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
        </div>
      )}

      {app.offer_amount && (
        <div className="text-xs text-green-700 font-semibold mb-2">
          ₹{app.offer_amount} LPA Offer
        </div>
      )}

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-50">
        <span className="text-xs text-gray-400">
          {new Date(app.applied_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
        </span>
        {next && (
          <button
            onClick={() => onStatusChange(next)}
            className="text-xs text-brand-600 hover:text-brand-700 font-medium flex items-center gap-0.5"
          >
            Move to {next.replace(/_/g, " ")}
            <ChevronDown className="w-3 h-3 rotate-[-90deg]" />
          </button>
        )}
      </div>
    </div>
  );
}
