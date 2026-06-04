import axios, { type AxiosInstance } from "axios";
import { getSession } from "next-auth/react";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT from NextAuth session on every request
api.interceptors.request.use(async (config) => {
  const session = await getSession();
  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const msg = error.response?.data?.detail ?? error.message ?? "Something went wrong";
    return Promise.reject(new Error(msg));
  }
);

// ─── Typed API helpers ────────────────────────────────────────────────────────

export const jobsApi = {
  getFeed: (limit = 20, offset = 0) =>
    api.get<JobCard[]>(`/jobs/feed?limit=${limit}&offset=${offset}`).then((r) => r.data),
  getOne: (id: string) =>
    api.get<JobCard>(`/jobs/${id}`).then((r) => r.data),
};

export const swipesApi = {
  record: (jobId: string, direction: "left" | "right" | "up", matchScore?: number) =>
    api.post("/swipes", { job_id: jobId, direction, match_score: matchScore }).then((r) => r.data),
  getSaved: () =>
    api.get("/swipes/saved").then((r) => r.data),
};

export const applicationsApi = {
  list: () => api.get<Application[]>("/applications").then((r) => r.data),
  updateStatus: (id: string, status: string, meta?: Record<string, unknown>) =>
    api.patch(`/applications/${id}/status`, { status, ...meta }).then((r) => r.data),
  withdraw: (id: string) => api.delete(`/applications/${id}`),
};

export const profileApi = {
  get: () => api.get<UserProfile>("/profile").then((r) => r.data),
  update: (data: Partial<UserProfile>) => api.put<UserProfile>("/profile", data).then((r) => r.data),
  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/profile/resume", form, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data);
  },
  getScore: () => api.get<{ score: number; missing: string[] }>("/profile/score").then((r) => r.data),
};

export const authApi = {
  sendOtp: (phone: string) => api.post("/auth/send-otp", { phone }).then((r) => r.data),
  verifyOtp: (phone: string, otp: string) =>
    api.post("/auth/verify-otp", { phone, otp }).then((r) => r.data),
  googleSignIn: (idToken: string, email: string, fullName?: string) =>
    api.post("/auth/google", { id_token: idToken, email, full_name: fullName }).then((r) => r.data),
};

// ─── Types (mirror backend schemas) ──────────────────────────────────────────

export interface JobCard {
  id: string;
  title: string;
  company: string;
  company_logo: string | null;
  location: string | null;
  is_remote: boolean;
  salary_min_lpa: number | null;
  salary_max_lpa: number | null;
  experience_min: number;
  experience_max: number;
  skills_required: string[];
  description: string | null;
  apply_url: string | null;
  job_type: string | null;
  industry: string | null;
  source: string;
  posted_at: string;
  match_score: number;
  score_details: Record<string, number>;
  highlights: string[];
}

export interface Application {
  id: string;
  job_id: string;
  title: string;
  company: string;
  company_logo: string | null;
  location: string | null;
  status: string;
  applied_at: string;
  updated_at: string;
  auto_applied: boolean;
  notes: string | null;
  interview_date: string | null;
  offer_amount: number | null;
  match_score: number | null;
}

export interface UserProfile {
  user_id: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  headline: string | null;
  skills: string[];
  experience_years: number;
  current_location: string | null;
  preferred_locations: string[];
  min_salary_lpa: number | null;
  max_salary_lpa: number | null;
  job_types: string[];
  notice_period_days: number;
  education: EducationEntry[];
  experience: ExperienceEntry[];
  projects: ProjectEntry[];
  profile_score: number;
  is_onboarded: boolean;
  resume_url: string | null;
}

export interface EducationEntry {
  degree: string;
  college: string;
  year: number | null;
  cgpa: number | null;
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
