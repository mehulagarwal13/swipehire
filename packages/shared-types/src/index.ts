// ─── Job ──────────────────────────────────────────────────────────────────────
export interface Job {
  id: string;
  title: string;
  company: string;
  companyLogo?: string;
  location?: string;
  isRemote: boolean;
  salaryMinLpa?: number;
  salaryMaxLpa?: number;
  experienceMin: number;
  experienceMax: number;
  skillsRequired: string[];
  description?: string;
  applyUrl?: string;
  jobType?: JobType;
  industry?: string;
  source: JobSource;
  postedAt: string;
  matchScore: number;
  scoreDetails: ScoreDetails;
  highlights: string[];
}

export type JobType = "full-time" | "part-time" | "internship" | "contract" | "freelance";
export type JobSource = "naukri" | "linkedin" | "internshala" | "instahyre" | "scraped" | "recruiter" | "seed";

export interface ScoreDetails {
  skills: number;
  experience: number;
  location: number;
  salary: number;
  semantic: number;
}

// ─── User ─────────────────────────────────────────────────────────────────────
export interface User {
  id: string;
  phone?: string;
  email?: string;
  fullName?: string;
  profilePhoto?: string;
  plan: UserPlan;
  isVerified: boolean;
  createdAt: string;
}

export type UserPlan = "free" | "pro" | "premium";

export interface UserProfile {
  userId: string;
  fullName?: string;
  email?: string;
  phone?: string;
  headline?: string;
  skills: string[];
  experienceYears: number;
  currentLocation?: string;
  preferredLocations: string[];
  minSalaryLpa?: number;
  maxSalaryLpa?: number;
  jobTypes: JobType[];
  noticePeriodDays: number;
  education: EducationEntry[];
  experience: ExperienceEntry[];
  projects: ProjectEntry[];
  profileScore: number;
  isOnboarded: boolean;
  resumeUrl?: string;
}

export interface EducationEntry {
  degree: string;
  college: string;
  year?: number;
  cgpa?: number;
}

export interface ExperienceEntry {
  company: string;
  role: string;
  duration: string;
  description: string;
}

export interface ProjectEntry {
  name: string;
  stack: string;
  link: string;
  description: string;
}

// ─── Swipe ────────────────────────────────────────────────────────────────────
export type SwipeDirection = "left" | "right" | "up";

export interface Swipe {
  id: string;
  userId: string;
  jobId: string;
  direction: SwipeDirection;
  matchScore?: number;
  swipedAt: string;
}

// ─── Application ──────────────────────────────────────────────────────────────
export type ApplicationStatus =
  | "applied"
  | "screening"
  | "interview_scheduled"
  | "interview_completed"
  | "offer_extended"
  | "offer_accepted"
  | "offer_rejected"
  | "rejected"
  | "withdrawn";

export interface Application {
  id: string;
  userId: string;
  jobId: string;
  job: Pick<Job, "title" | "company" | "companyLogo" | "location">;
  status: ApplicationStatus;
  appliedAt: string;
  updatedAt: string;
  autoApplied: boolean;
  notes?: string;
  interviewDate?: string;
  offerAmount?: number;
  matchScore?: number;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  userId: string;
  isOnboarded: boolean;
}

// ─── API Pagination ───────────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

// ─── Plan limits ──────────────────────────────────────────────────────────────
export const PLAN_LIMITS: Record<UserPlan, { swipesPerDay: number; autoApply: boolean }> = {
  free:    { swipesPerDay: 20,       autoApply: false },
  pro:     { swipesPerDay: Infinity, autoApply: true  },
  premium: { swipesPerDay: Infinity, autoApply: true  },
};
