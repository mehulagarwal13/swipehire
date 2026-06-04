"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { profileApi } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, ArrowRight, ArrowLeft, CheckCircle2, Upload, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { useRef } from "react";

const SKILLS = [
  "JavaScript","TypeScript","React","Node.js","Python","Java","SQL","AWS",
  "Docker","Git","MongoDB","PostgreSQL","Machine Learning","FastAPI","Next.js",
  "React Native","Spring Boot","Kubernetes","GraphQL","Redis","Flutter","Go",
  "Rust","C++","Scala","Kafka","Elasticsearch","Terraform","CI/CD","Figma",
];

const LOCATIONS = [
  "Bangalore","Mumbai","Delhi NCR","Hyderabad","Pune",
  "Chennai","Kolkata","Ahmedabad","Jaipur","Remote",
];

const JOB_TYPES = [
  { value: "full-time",   label: "Full Time",   emoji: "🏢" },
  { value: "internship",  label: "Internship",  emoji: "🎓" },
  { value: "contract",    label: "Contract",    emoji: "📋" },
  { value: "remote",      label: "Remote Only", emoji: "🌍" },
];

const EXP_OPTIONS = [
  { label: "Fresher (0 yrs)", value: 0 },
  { label: "< 1 year",        value: 0.5 },
  { label: "1–2 years",       value: 1.5 },
  { label: "3–5 years",       value: 4 },
  { label: "5–8 years",       value: 6.5 },
  { label: "8+ years",        value: 9 },
];

interface FormData {
  skills: string[];
  preferred_locations: string[];
  job_types: string[];
  experience_years: number;
  min_salary_lpa: number;
  max_salary_lpa: number;
  headline: string;
}

const TOTAL_STEPS = 5;

export default function OnboardingPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState(1);
  const [resumeUploaded, setResumeUploaded] = useState(false);
  const [form, setForm] = useState<FormData>({
    skills: [],
    preferred_locations: [],
    job_types: [],
    experience_years: 0,
    min_salary_lpa: 3,
    max_salary_lpa: 10,
    headline: "",
  });

  const updateMutation = useMutation({
    mutationFn: profileApi.update,
    onSuccess: () => router.push("/swipe"),
    onError: (e: Error) => toast.error(e.message),
  });

  const resumeMutation = useMutation({
    mutationFn: profileApi.uploadResume,
    onSuccess: (data) => {
      setResumeUploaded(true);
      // Pre-fill form from parsed resume
      if (data.parsed.skills?.length) setForm(f => ({ ...f, skills: data.parsed.skills }));
      if (data.parsed.experience_years) setForm(f => ({ ...f, experience_years: data.parsed.experience_years }));
      if (data.parsed.headline) setForm(f => ({ ...f, headline: data.parsed.headline }));
      toast.success("Resume parsed! Fields pre-filled.");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const toggle = (field: keyof FormData, value: string) => {
    setForm(f => {
      const arr = f[field] as string[];
      return {
        ...f,
        [field]: arr.includes(value) ? arr.filter(v => v !== value) : [...arr, value],
      };
    });
  };

  const canProceed = () => {
    if (step === 1) return true; // resume optional
    if (step === 2) return form.skills.length >= 3;
    if (step === 3) return form.preferred_locations.length >= 1;
    if (step === 4) return form.job_types.length >= 1;
    return true;
  };

  const handleFinish = () => {
    updateMutation.mutate({
      ...form,
      job_types: form.job_types.filter(t => t !== "remote"),
      preferred_locations: form.job_types.includes("remote")
        ? [...form.preferred_locations, "Remote"]
        : form.preferred_locations,
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 via-white to-blue-50 flex flex-col items-center justify-center p-4">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Zap className="w-6 h-6 text-brand-500" />
          <span className="text-xl font-bold text-gray-900">SwipeHire</span>
        </div>
        <p className="text-gray-500 text-sm">Let's set up your profile in {TOTAL_STEPS} quick steps</p>
      </div>

      {/* Progress bar */}
      <div className="w-full max-w-lg mb-8">
        <div className="flex gap-1.5">
          {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${
                i < step ? "bg-brand-500" : "bg-gray-200"
              }`}
            />
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-2 text-right">Step {step} of {TOTAL_STEPS}</p>
      </div>

      {/* Card */}
      <div className="w-full max-w-lg">
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -30 }}
            transition={{ duration: 0.25 }}
            className="bg-white rounded-3xl shadow-xl p-8 border border-gray-100"
          >
            {/* Step 1: Resume Upload */}
            {step === 1 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Upload your resume</h2>
                <p className="text-gray-500 text-sm mb-6">
                  AI will extract your skills and experience. Skip if you prefer to fill manually.
                </p>
                <div
                  onClick={() => fileRef.current?.click()}
                  className={`border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer transition-colors ${
                    resumeUploaded
                      ? "border-brand-400 bg-brand-50"
                      : "border-gray-200 hover:border-brand-300 hover:bg-gray-50"
                  }`}
                >
                  {resumeMutation.isPending ? (
                    <div className="flex flex-col items-center gap-2">
                      <Loader2 className="w-10 h-10 animate-spin text-brand-500" />
                      <p className="text-brand-600 font-medium">Parsing with AI…</p>
                    </div>
                  ) : resumeUploaded ? (
                    <div className="flex flex-col items-center gap-2">
                      <CheckCircle2 className="w-10 h-10 text-brand-500" />
                      <p className="text-brand-700 font-semibold">Resume parsed successfully!</p>
                      <p className="text-xs text-gray-400">Click to replace</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <Upload className="w-10 h-10 text-gray-300" />
                      <p className="text-gray-600 font-medium">Drop PDF or DOCX here</p>
                      <p className="text-xs text-gray-400">Max 5 MB</p>
                    </div>
                  )}
                </div>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.docx"
                  className="hidden"
                  onChange={e => {
                    const f = e.target.files?.[0];
                    if (f) resumeMutation.mutate(f);
                  }}
                />
              </div>
            )}

            {/* Step 2: Skills */}
            {step === 2 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Your tech skills</h2>
                <p className="text-gray-500 text-sm mb-6">
                  Pick at least 3. These power your job match score.
                </p>
                <div className="flex flex-wrap gap-2 max-h-64 overflow-y-auto no-scrollbar">
                  {SKILLS.map(skill => (
                    <button
                      key={skill}
                      type="button"
                      onClick={() => toggle("skills", skill)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                        form.skills.includes(skill)
                          ? "bg-brand-500 text-white border-brand-500 scale-105"
                          : "bg-white text-gray-600 border-gray-200 hover:border-brand-300"
                      }`}
                    >
                      {skill}
                    </button>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-3">{form.skills.length} selected</p>
              </div>
            )}

            {/* Step 3: Locations */}
            {step === 3 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Where do you want to work?</h2>
                <p className="text-gray-500 text-sm mb-6">Select all that apply.</p>
                <div className="grid grid-cols-2 gap-3">
                  {LOCATIONS.map(loc => (
                    <button
                      key={loc}
                      type="button"
                      onClick={() => toggle("preferred_locations", loc)}
                      className={`py-3 px-4 rounded-2xl text-sm font-medium border transition-all text-left ${
                        form.preferred_locations.includes(loc)
                          ? "bg-brand-500 text-white border-brand-500"
                          : "bg-white text-gray-700 border-gray-200 hover:border-brand-300"
                      }`}
                    >
                      {loc === "Remote" ? "🌍 " : "📍 "}{loc}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Step 4: Job type + Experience */}
            {step === 4 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Job preferences</h2>
                <p className="text-gray-500 text-sm mb-5">What kind of role are you looking for?</p>

                <p className="text-sm font-semibold text-gray-700 mb-3">Job type</p>
                <div className="grid grid-cols-2 gap-3 mb-6">
                  {JOB_TYPES.map(jt => (
                    <button
                      key={jt.value}
                      type="button"
                      onClick={() => toggle("job_types", jt.value)}
                      className={`py-3 px-4 rounded-2xl text-sm font-medium border transition-all ${
                        form.job_types.includes(jt.value)
                          ? "bg-brand-500 text-white border-brand-500"
                          : "bg-white text-gray-700 border-gray-200 hover:border-brand-300"
                      }`}
                    >
                      {jt.emoji} {jt.label}
                    </button>
                  ))}
                </div>

                <p className="text-sm font-semibold text-gray-700 mb-3">Experience level</p>
                <div className="grid grid-cols-3 gap-2">
                  {EXP_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setForm(f => ({ ...f, experience_years: opt.value }))}
                      className={`py-2.5 px-3 rounded-xl text-xs font-medium border transition-all ${
                        form.experience_years === opt.value
                          ? "bg-brand-500 text-white border-brand-500"
                          : "bg-white text-gray-700 border-gray-200 hover:border-brand-300"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Step 5: Salary */}
            {step === 5 && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Salary expectation</h2>
                <p className="text-gray-500 text-sm mb-6">
                  In Lakhs Per Annum (LPA). This improves your match quality.
                </p>

                <div className="space-y-6">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <label className="text-sm font-medium text-gray-700">Minimum</label>
                      <span className="text-brand-600 font-bold">₹{form.min_salary_lpa} LPA</span>
                    </div>
                    <input
                      type="range"
                      min={2} max={50} step={0.5}
                      value={form.min_salary_lpa}
                      onChange={e => setForm(f => ({ ...f, min_salary_lpa: +e.target.value }))}
                      className="w-full accent-brand-500"
                    />
                  </div>
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <label className="text-sm font-medium text-gray-700">Maximum</label>
                      <span className="text-brand-600 font-bold">₹{form.max_salary_lpa} LPA</span>
                    </div>
                    <input
                      type="range"
                      min={form.min_salary_lpa} max={100} step={0.5}
                      value={form.max_salary_lpa}
                      onChange={e => setForm(f => ({ ...f, max_salary_lpa: +e.target.value }))}
                      className="w-full accent-brand-500"
                    />
                  </div>

                  <div className="bg-brand-50 rounded-2xl p-4 text-center">
                    <p className="text-brand-700 font-semibold text-lg">
                      ₹{form.min_salary_lpa} – ₹{form.max_salary_lpa} LPA
                    </p>
                    <p className="text-brand-500 text-xs mt-1">Your target range</p>
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex gap-3 mt-6">
          {step > 1 && (
            <button
              onClick={() => setStep(s => s - 1)}
              className="flex items-center gap-2 px-5 py-3 rounded-2xl border border-gray-200 text-gray-600 hover:bg-gray-50 font-medium text-sm transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>
          )}
          {step === 1 && (
            <button
              onClick={() => setStep(s => s + 1)}
              className="flex-1 py-3 rounded-2xl border border-gray-200 text-gray-500 hover:bg-gray-50 font-medium text-sm transition-colors"
            >
              Skip for now
            </button>
          )}
          <button
            onClick={() => step < TOTAL_STEPS ? setStep(s => s + 1) : handleFinish()}
            disabled={!canProceed() || updateMutation.isPending}
            className="flex-1 flex items-center justify-center gap-2 py-3 bg-brand-500 hover:bg-brand-600 text-white font-semibold rounded-2xl transition-colors disabled:opacity-50"
          >
            {updateMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : step === TOTAL_STEPS ? (
              <>Start Swiping <Zap className="w-4 h-4" /></>
            ) : (
              <>Continue <ArrowRight className="w-4 h-4" /></>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
