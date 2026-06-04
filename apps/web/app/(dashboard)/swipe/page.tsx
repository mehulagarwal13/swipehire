"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { SwipeDeck } from "@/components/swipe/SwipeDeck";
import { jobsApi } from "@/lib/api";
import type { JobCard } from "@/lib/api";

const PAGE_SIZE = 20;

export default function SwipePage() {
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading, isError } =
    useInfiniteQuery({
      queryKey: ["jobs", "feed"],
      queryFn: ({ pageParam = 0 }) => jobsApi.getFeed(PAGE_SIZE, pageParam as number),
      getNextPageParam: (lastPage, allPages) => {
        if ((lastPage as JobCard[]).length < PAGE_SIZE) return undefined;
        return allPages.length * PAGE_SIZE;
      },
      initialPageParam: 0,
    });

  const allJobs = data?.pages.flat() ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
          <p className="text-gray-500">Loading your personalized feed…</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-red-500">Failed to load jobs. Please refresh.</p>
      </div>
    );
  }

  return (
    <div className="h-full p-4">
      <SwipeDeck
        jobs={allJobs}
        onLoadMore={() => hasNextPage && fetchNextPage()}
        isLoadingMore={isFetchingNextPage}
      />
    </div>
  );
}
