"use client";

import { useState, useTransition } from "react";
import { Search, X, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { jobsApi, type JobCard } from "@/lib/api";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { MatchBadge } from "./MatchBadge";

interface SearchBarProps {
  onSelectJob?: (job: JobCard) => void;
}

async function searchJobs(q: string): Promise<JobCard[]> {
  if (!q.trim()) return [];
  return api.get<JobCard[]>(`/jobs/search?q=${encodeURIComponent(q)}&limit=10`).then(r => r.data);
}

export function SearchBar({ onSelectJob }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const { data: results = [], isFetching } = useQuery({
    queryKey: ["job-search", query],
    queryFn: () => searchJobs(query),
    enabled: query.length >= 2,
    staleTime: 30_000,
  });

  return (
    <div className="relative w-full max-w-md">
      {/* Input */}
      <div className="relative">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 200)}
          placeholder="Search jobs, skills, companies…"
          className="w-full pl-10 pr-10 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-300 focus:border-transparent transition-all"
        />
        {query && (
          <button
            onClick={() => { setQuery(""); setOpen(false); }}
            className="absolute right-3.5 top-1/2 -translate-y-1/2"
          >
            {isFetching
              ? <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
              : <X className="w-4 h-4 text-gray-400 hover:text-gray-600" />
            }
          </button>
        )}
      </div>

      {/* Dropdown results */}
      {open && query.length >= 2 && (
        <div className="absolute top-full mt-2 left-0 right-0 bg-white rounded-2xl shadow-xl border border-gray-100 z-50 overflow-hidden">
          {results.length === 0 && !isFetching && (
            <div className="p-4 text-center text-sm text-gray-400">
              No results for "{query}"
            </div>
          )}
          {results.map(job => (
            <button
              key={job.id}
              onMouseDown={() => { onSelectJob?.(job); setQuery(""); setOpen(false); }}
              className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-start gap-3 border-b border-gray-50 last:border-0 transition-colors"
            >
              <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-500 flex-shrink-0 mt-0.5">
                {job.company[0]}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 truncate">{job.title}</p>
                <p className="text-xs text-gray-500">{job.company} · {job.location ?? "Remote"}</p>
              </div>
              {job.match_score > 0 && (
                <MatchBadge score={job.match_score} size="sm" showLabel={false} />
              )}
            </button>
          ))}
          {results.length > 0 && (
            <div className="px-4 py-2 bg-gray-50 text-xs text-gray-400 text-right">
              {results.length} results · powered by Meilisearch
            </div>
          )}
        </div>
      )}
    </div>
  );
}
