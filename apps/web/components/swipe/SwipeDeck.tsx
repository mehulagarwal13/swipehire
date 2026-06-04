"use client";

import { useState, useCallback } from "react";
import { ThumbsDown, ThumbsUp, Bookmark, RefreshCw, Loader2 } from "lucide-react";
import { JobCard } from "./JobCard";
import { swipesApi, type JobCard as JobCardType } from "@/lib/api";
import toast from "react-hot-toast";
import { useSwipeStore } from "@/lib/store";

interface SwipeDeckProps {
  jobs: JobCardType[];
  onLoadMore: () => void;
  isLoadingMore: boolean;
}

export function SwipeDeck({ jobs, onLoadMore, isLoadingMore }: SwipeDeckProps) {
  const [topIndex, setTopIndex] = useState(0);
  const { incrementSwipes } = useSwipeStore();

  const currentJob = jobs[topIndex];
  const nextJob     = jobs[topIndex + 1];
  const thirdJob    = jobs[topIndex + 2];

  const handleSwipe = useCallback(
    async (direction: "left" | "right" | "up") => {
      if (!currentJob) return;

      incrementSwipes();

      try {
        await swipesApi.record(currentJob.id, direction, currentJob.match_score);

        const msgs: Record<string, string> = {
          right: `✅ Applied to ${currentJob.title}`,
          left:  "Skipped",
          up:    `🔖 Saved ${currentJob.title}`,
        };
        if (direction !== "left") toast.success(msgs[direction]);
      } catch (err: unknown) {
        toast.error(err instanceof Error ? err.message : "Failed to record swipe");
      }

      const nextIndex = topIndex + 1;
      setTopIndex(nextIndex);

      // Load more when 3 cards remain
      if (jobs.length - nextIndex <= 3) {
        onLoadMore();
      }
    },
    [currentJob, topIndex, jobs.length, onLoadMore, incrementSwipes]
  );

  if (!currentJob) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-gray-500">
        <RefreshCw className="w-12 h-12 text-gray-300" />
        <p className="text-lg font-medium">You've seen all jobs!</p>
        <p className="text-sm text-gray-400">Check back later for more matches.</p>
        {isLoadingMore && (
          <div className="flex items-center gap-2 text-brand-600">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Loading more jobs…</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-6">
      {/* Card stack */}
      <div className="relative flex-1 max-w-md mx-auto w-full">
        {thirdJob && (
          <JobCard job={thirdJob} onSwipe={handleSwipe} isTop={false} stackIndex={2} />
        )}
        {nextJob && (
          <JobCard job={nextJob} onSwipe={handleSwipe} isTop={false} stackIndex={1} />
        )}
        <JobCard job={currentJob} onSwipe={handleSwipe} isTop stackIndex={0} />
      </div>

      {/* Action buttons */}
      <div className="flex items-center justify-center gap-6 pb-4">
        <ActionButton
          onClick={() => handleSwipe("left")}
          icon={<ThumbsDown className="w-6 h-6" />}
          label="Skip"
          color="red"
        />
        <ActionButton
          onClick={() => handleSwipe("up")}
          icon={<Bookmark className="w-5 h-5" />}
          label="Save"
          color="blue"
          size="sm"
        />
        <ActionButton
          onClick={() => handleSwipe("right")}
          icon={<ThumbsUp className="w-6 h-6" />}
          label="Apply"
          color="green"
        />
      </div>
    </div>
  );
}

function ActionButton({
  onClick,
  icon,
  label,
  color,
  size = "md",
}: {
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  color: "red" | "green" | "blue";
  size?: "sm" | "md";
}) {
  const colorClasses = {
    red:   "bg-white border-red-200   text-red-500   hover:bg-red-50   hover:border-red-400   active:scale-95",
    green: "bg-white border-green-200 text-green-600 hover:bg-green-50 hover:border-green-400 active:scale-95",
    blue:  "bg-white border-blue-200  text-blue-500  hover:bg-blue-50  hover:border-blue-400  active:scale-95",
  };

  const sizeClass = size === "sm" ? "w-12 h-12" : "w-16 h-16";

  return (
    <button
      onClick={onClick}
      aria-label={label}
      className={`${sizeClass} rounded-full border-2 flex items-center justify-center shadow-md transition-all duration-150 ${colorClasses[color]}`}
    >
      {icon}
    </button>
  );
}
