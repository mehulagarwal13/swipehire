"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { profileApi, type UserProfile } from "@/lib/api";
import { Upload, Star, CheckCircle2, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { useRef } from "react";
import { MatchBadge } from "@/components/swipe/MatchBadge";

const SKILLS_SUGGESTIONS = [
  "JavaScript","TypeScript","React","Node.js","Python","Java","SQL",
  "AWS","Docker","Git","MongoDB","PostgreSQL","Machine Learning","FastAPI",
  "Next.js","React Native","Spring Boot","Kubernetes","GraphQL","Redis",
];

const LOCATIONS = [
  "Bangalore","Mumbai","Delhi NCR","Hyderabad","Pune","Chennai",
  "Kolkata","Ahmedabad","Jaipur","Remote",
];

const JOB_TYPES = ["full-time","part-time","internship","contract","freelance"];

export default function ProfilePage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: profileApi.get,
  });

  const { data: scoreData } = useQuery({
    queryKey: ["profile-score"],
    queryFn: profileApi.getScore,
  });

  const updateMutation = useMutation({
    mutationFn: profileApi.update,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      qc.invalidateQueries({ queryKey: ["profile-score"] });
      toast.success("Profile updated!");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const resumeMutation = useMutation({
    mutationFn: profileApi.uploadResume,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      toast.success(`Resume parsed! ${data.parsed.skills?.length ?? 0} skills extracted.`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const { register, handleSubmit, control, watch, setValue } =
    useForm<Partial<UserProfile>>({ values: profile });

  const selectedSkills = watch("skills") ?? [];
  const selectedLocations = watch("preferred_locations") ?? [];
  const selectedJobTypes = watch("job_types") ?? [];

  const toggleItem = (field: "skills" | "preferred_locations" | "job_types", item: string) => {
    const current = watch(field) as string[] ?? [];
    const updated = current.includes(item)
      ? current.filter((s) => s !== item)
      : [...current, item];
    setValue(field, updated as never);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6 pb-20">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Your Profile</h1>
        {scoreData && (
          <div className="mt-4 p-4 bg-gray-50 rounded-2xl">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">Profile Completeness</span>
              <span className="text-lg font-bold text-brand-600">{scoreData.score}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-brand-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${scoreData.score}%` }}
              />
            </div>
            {scoreData.missing.length > 0 && (
              <ul className="mt-3 space-y-1">
                {scoreData.missing.map((m) => (
                  <li key={m} className="text-xs text-amber-700 flex items-center gap-1.5">
                    <Star className="w-3 h-3 flex-shrink-0" />
                    {m}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {/* Resume upload */}
      <section className="mb-8">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Resume</h2>
        <div
          onClick={() => fileRef.current?.click()}
          className="border-2 border-dashed border-gray-300 rounded-2xl p-8 text-center cursor-pointer hover:border-brand-400 hover:bg-brand-50 transition-colors"
        >
          {resumeMutation.isPending ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
              <p className="text-sm text-brand-600">Parsing resume with AI…</p>
            </div>
          ) : profile?.resume_url ? (
            <div className="flex flex-col items-center gap-2">
              <CheckCircle2 className="w-8 h-8 text-brand-500" />
              <p className="text-sm font-medium text-brand-600">Resume uploaded ✓</p>
              <p className="text-xs text-gray-400">Click to replace</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="w-8 h-8 text-gray-400" />
              <p className="text-sm font-medium text-gray-600">Upload PDF or DOCX</p>
              <p className="text-xs text-gray-400">AI will extract your skills & experience</p>
            </div>
          )}
        </div>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) resumeMutation.mutate(file);
          }}
        />
      </section>

      <form onSubmit={handleSubmit((data) => updateMutation.mutate(data))}>
        {/* Basic info */}
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Basic Info</h2>
          <div className="space-y-4">
            <Field label="Headline" placeholder="e.g. Full-stack Developer, 2 yrs exp">
              <input {...register("headline")} className="input" />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Experience (years)">
                <input type="number" step="0.5" min="0" {...register("experience_years", { valueAsNumber: true })} className="input" />
              </Field>
              <Field label="Notice Period (days)">
                <input type="number" min="0" {...register("notice_period_days", { valueAsNumber: true })} className="input" />
              </Field>
            </div>
            <Field label="Current Location">
              <input {...register("current_location")} placeholder="e.g. Bangalore, KA" className="input" />
            </Field>
          </div>
        </section>

        {/* Salary expectations */}
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Salary Expectation (LPA)</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Min (₹ LPA)">
              <input type="number" step="0.5" {...register("min_salary_lpa", { valueAsNumber: true })} className="input" />
            </Field>
            <Field label="Max (₹ LPA)">
              <input type="number" step="0.5" {...register("max_salary_lpa", { valueAsNumber: true })} className="input" />
            </Field>
          </div>
        </section>

        {/* Skills */}
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Skills</h2>
          <div className="flex flex-wrap gap-2">
            {SKILLS_SUGGESTIONS.map((skill) => (
              <button
                type="button"
                key={skill}
                onClick={() => toggleItem("skills", skill)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                  selectedSkills.includes(skill)
                    ? "bg-brand-500 text-white border-brand-500"
                    : "bg-white text-gray-600 border-gray-200 hover:border-brand-300"
                }`}
              >
                {skill}
              </button>
            ))}
          </div>
        </section>

        {/* Preferred locations */}
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Preferred Locations</h2>
          <div className="flex flex-wrap gap-2">
            {LOCATIONS.map((loc) => (
              <button
                type="button"
                key={loc}
                onClick={() => toggleItem("preferred_locations", loc)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                  selectedLocations.includes(loc)
                    ? "bg-brand-500 text-white border-brand-500"
                    : "bg-white text-gray-600 border-gray-200 hover:border-brand-300"
                }`}
              >
                {loc}
              </button>
            ))}
          </div>
        </section>

        {/* Job types */}
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Job Types</h2>
          <div className="flex flex-wrap gap-2">
            {JOB_TYPES.map((jt) => (
              <button
                type="button"
                key={jt}
                onClick={() => toggleItem("job_types", jt)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium border capitalize transition-colors ${
                  selectedJobTypes.includes(jt)
                    ? "bg-brand-500 text-white border-brand-500"
                    : "bg-white text-gray-600 border-gray-200 hover:border-brand-300"
                }`}
              >
                {jt}
              </button>
            ))}
          </div>
        </section>

        <button
          type="submit"
          disabled={updateMutation.isPending}
          className="w-full py-3.5 bg-brand-500 hover:bg-brand-600 text-white font-semibold rounded-2xl transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
        >
          {updateMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
          Save Profile
        </button>
      </form>
    </div>
  );
}

function Field({
  label,
  placeholder,
  children,
}: {
  label: string;
  placeholder?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      {children}
    </div>
  );
}
