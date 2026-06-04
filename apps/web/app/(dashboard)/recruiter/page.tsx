"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type JobCard } from "@/lib/api";
import { Plus, Briefcase, Users, Eye, Loader2, X } from "lucide-react";
import toast from "react-hot-toast";

// ─── Recruiter API helpers ────────────────────────────────────────────────────

const recruiterApi = {
  getMyJobs: () => api.get<JobCard[]>("/jobs?source=recruiter").then(r => r.data),
  createJob:  (data: CreateJobForm) => api.post<JobCard>("/jobs", data).then(r => r.data),
};

interface CreateJobForm {
  title: string;
  company: string;
  location: string;
  is_remote: boolean;
  salary_min_lpa: number;
  salary_max_lpa: number;
  experience_min: number;
  experience_max: number;
  skills_required: string[];
  description: string;
  apply_url: string;
  job_type: string;
  industry: string;
}

const DEFAULT_FORM: CreateJobForm = {
  title: "", company: "", location: "", is_remote: false,
  salary_min_lpa: 5, salary_max_lpa: 15, experience_min: 0, experience_max: 3,
  skills_required: [], description: "", apply_url: "", job_type: "full-time", industry: "",
};

const INDUSTRIES = ["Engineering","Data","AI/ML","Product","Design","QA","DevOps","Mobile","Security","Cloud"];
const JOB_TYPES  = ["full-time","part-time","internship","contract","freelance"];

// ─── Post Job modal ───────────────────────────────────────────────────────────

function PostJobModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [form, setForm] = useState<CreateJobForm>(DEFAULT_FORM);
  const [skillInput, setSkillInput] = useState("");

  const createMutation = useMutation({
    mutationFn: recruiterApi.createJob,
    onSuccess: () => { toast.success("Job posted!"); onSuccess(); onClose(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const addSkill = () => {
    const s = skillInput.trim();
    if (s && !form.skills_required.includes(s)) {
      setForm(f => ({ ...f, skills_required: [...f.skills_required, s] }));
    }
    setSkillInput("");
  };

  const f = (field: keyof CreateJobForm) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => setForm(prev => ({ ...prev, [field]: e.target.value }));

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-100 px-8 py-5 flex items-center justify-between rounded-t-3xl">
          <h2 className="text-xl font-bold text-gray-900">Post a Job</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-xl"><X className="w-5 h-5" /></button>
        </div>

        <div className="p-8 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Job Title *">
              <input value={form.title} onChange={f("title")} className="input" placeholder="e.g. Senior React Developer" required />
            </Field>
            <Field label="Company *">
              <input value={form.company} onChange={f("company")} className="input" placeholder="Your company name" required />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Location">
              <input value={form.location} onChange={f("location")} className="input" placeholder="Bangalore, KA" />
            </Field>
            <Field label="Industry">
              <select value={form.industry} onChange={f("industry")} className="input">
                <option value="">Select industry</option>
                {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
              </select>
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Job Type">
              <select value={form.job_type} onChange={f("job_type")} className="input">
                {JOB_TYPES.map(t => <option key={t} value={t} className="capitalize">{t}</option>)}
              </select>
            </Field>
            <Field label="Remote?">
              <div className="flex items-center gap-3 mt-2">
                <button
                  type="button"
                  onClick={() => setForm(f => ({ ...f, is_remote: !f.is_remote }))}
                  className={`w-12 h-6 rounded-full transition-colors ${form.is_remote ? "bg-brand-500" : "bg-gray-300"}`}
                >
                  <span className={`block w-5 h-5 bg-white rounded-full shadow transition-transform mx-0.5 ${form.is_remote ? "translate-x-6" : ""}`} />
                </button>
                <span className="text-sm text-gray-600">{form.is_remote ? "Yes" : "No"}</span>
              </div>
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Min Salary (LPA)">
              <input type="number" value={form.salary_min_lpa} onChange={f("salary_min_lpa")} className="input" min={0} step={0.5} />
            </Field>
            <Field label="Max Salary (LPA)">
              <input type="number" value={form.salary_max_lpa} onChange={f("salary_max_lpa")} className="input" min={0} step={0.5} />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Min Experience (yrs)">
              <input type="number" value={form.experience_min} onChange={f("experience_min")} className="input" min={0} step={0.5} />
            </Field>
            <Field label="Max Experience (yrs)">
              <input type="number" value={form.experience_max} onChange={f("experience_max")} className="input" min={0} step={0.5} />
            </Field>
          </div>

          <Field label="Required Skills">
            <div className="flex gap-2 mb-2">
              <input
                value={skillInput}
                onChange={e => setSkillInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addSkill())}
                className="input flex-1"
                placeholder="Type skill + Enter"
              />
              <button type="button" onClick={addSkill} className="px-4 py-2 bg-brand-500 text-white rounded-xl text-sm font-medium">Add</button>
            </div>
            <div className="flex flex-wrap gap-2">
              {form.skills_required.map(s => (
                <span key={s} className="flex items-center gap-1 px-3 py-1 bg-brand-50 text-brand-700 rounded-full text-sm">
                  {s}
                  <button onClick={() => setForm(f => ({ ...f, skills_required: f.skills_required.filter(x => x !== s) }))}>
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </Field>

          <Field label="Apply URL">
            <input value={form.apply_url} onChange={f("apply_url")} className="input" placeholder="https://careers.yourcompany.com/..." />
          </Field>

          <Field label="Job Description *">
            <textarea
              value={form.description}
              onChange={f("description")}
              className="input h-32 resize-none"
              placeholder="Describe the role, responsibilities, and what you're looking for…"
            />
          </Field>

          <button
            onClick={() => createMutation.mutate(form)}
            disabled={!form.title || !form.company || createMutation.isPending}
            className="w-full py-4 bg-brand-500 hover:bg-brand-600 text-white font-bold rounded-2xl transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {createMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            Post Job
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      {children}
    </div>
  );
}

// ─── Recruiter page ───────────────────────────────────────────────────────────

export default function RecruiterPage() {
  const [showModal, setShowModal] = useState(false);
  const qc = useQueryClient();

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["recruiter-jobs"],
    queryFn: recruiterApi.getMyJobs,
  });

  const stats = [
    { label: "Jobs Posted",    value: jobs.length,                              icon: Briefcase },
    { label: "Active Listings",value: jobs.filter(j => j.match_score >= 0).length, icon: Eye },
    { label: "Total Matches",  value: jobs.reduce((a, _) => a + 0, 0),          icon: Users },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recruiter Portal</h1>
          <p className="text-gray-500 text-sm mt-1">Post jobs and find the best talent</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-5 py-3 bg-brand-500 hover:bg-brand-600 text-white font-semibold rounded-2xl transition-colors"
        >
          <Plus className="w-4 h-4" />
          Post a Job
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {stats.map(s => (
          <div key={s.label} className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm flex items-center gap-4">
            <div className="w-10 h-10 bg-brand-50 rounded-xl flex items-center justify-center">
              <s.icon className="w-5 h-5 text-brand-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{s.value}</p>
              <p className="text-xs text-gray-500">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Job listings */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-brand-500" /></div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-3xl border border-dashed border-gray-200">
          <Briefcase className="w-12 h-12 text-gray-200 mx-auto mb-4" />
          <p className="text-gray-500 font-medium">No jobs posted yet</p>
          <p className="text-gray-400 text-sm mt-1">Click "Post a Job" to get started</p>
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map(job => (
            <div key={job.id} className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{job.title}</h3>
                  <p className="text-sm text-gray-500 mt-0.5">{job.company} · {job.location ?? "Remote"}</p>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {job.skills_required.slice(0, 4).map(s => (
                      <span key={s} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full text-xs">{s}</span>
                    ))}
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">Active</span>
                  {(job.salary_min_lpa || job.salary_max_lpa) && (
                    <p className="text-sm text-gray-500 mt-2">₹{job.salary_min_lpa}–{job.salary_max_lpa} LPA</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <PostJobModal
          onClose={() => setShowModal(false)}
          onSuccess={() => qc.invalidateQueries({ queryKey: ["recruiter-jobs"] })}
        />
      )}
    </div>
  );
}
