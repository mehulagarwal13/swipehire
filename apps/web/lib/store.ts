import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { JobCard, UserProfile } from "./api";

interface SwipeState {
  // Job feed
  feedJobs: JobCard[];
  currentIndex: number;
  setFeed: (jobs: JobCard[]) => void;
  appendFeed: (jobs: JobCard[]) => void;
  advanceIndex: () => void;

  // Auth
  accessToken: string | null;
  setAccessToken: (token: string | null) => void;

  // Profile
  profile: UserProfile | null;
  setProfile: (profile: UserProfile | null) => void;

  // Swipe counters (for free tier limit)
  swipesToday: number;
  lastSwipeDate: string | null;
  incrementSwipes: () => void;
}

export const useSwipeStore = create<SwipeState>()(
  persist(
    (set, get) => ({
      feedJobs: [],
      currentIndex: 0,
      setFeed: (jobs) => set({ feedJobs: jobs, currentIndex: 0 }),
      appendFeed: (jobs) =>
        set((s) => ({ feedJobs: [...s.feedJobs, ...jobs] })),
      advanceIndex: () =>
        set((s) => ({ currentIndex: s.currentIndex + 1 })),

      accessToken: null,
      setAccessToken: (token) => set({ accessToken: token }),

      profile: null,
      setProfile: (profile) => set({ profile }),

      swipesToday: 0,
      lastSwipeDate: null,
      incrementSwipes: () => {
        const today = new Date().toDateString();
        const { lastSwipeDate, swipesToday } = get();
        if (lastSwipeDate !== today) {
          set({ swipesToday: 1, lastSwipeDate: today });
        } else {
          set({ swipesToday: swipesToday + 1 });
        }
      },
    }),
    {
      name: "swipehire-store",
      partialize: (s) => ({
        accessToken: s.accessToken,
        swipesToday: s.swipesToday,
        lastSwipeDate: s.lastSwipeDate,
      }),
    }
  )
);
