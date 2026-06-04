"use client";

import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import Image from "next/image";
import { MapPin, Clock, Briefcase, IndianRupee, Wifi } from "lucide-react";
import { MatchBadge } from "./MatchBadge";
import type { JobCard as JobCardType } from "@/lib/api";
import { cn } from "@/lib/utils";

interface JobCardProps {
  job: JobCardType;
  onSwipe: (direction: "left" | "right" | "up") => void;
  isTop: boolean;
  stackIndex: number; // 0 = top, 1 = next, 2 = third
}

const SWIPE_THRESHOLD = 120;

export function JobCard({ job, onSwipe, isTop, stackIndex }: JobCardProps) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotate = useTransform(x, [-200, 200], [-18, 18]);

  // Overlay opacity for left/right visual feedback
  const applyOpacity  = useTransform(x, [0, SWIPE_THRESHOLD], [0, 1]);
  const skipOpacity   = useTransform(x, [-SWIPE_THRESHOLD, 0], [1, 0]);
  const saveOpacity   = useTransform(y, [-SWIPE_THRESHOLD, 0], [1, 0]);

  const handleDragEnd = (_: unknown, info: { offset: { x: number; y: number } }) => {
    if (info.offset.x > SWIPE_THRESHOLD) {
      animate(x, 600, { duration: 0.3 });
      onSwipe("right");
    } else if (info.offset.x < -SWIPE_THRESHOLD) {
      animate(x, -600, { duration: 0.3 });
      onSwipe("left");
    } else if (info.offset.y < -SWIPE_THRESHOLD) {
      animate(y, -600, { duration: 0.3 });
      onSwipe("up");
    } else {
      animate(x, 0, { type: "spring", stiffness: 400, damping: 25 });
      animate(y, 0, { type: "spring", stiffness: 400, damping: 25 });
    }
  };

  // Stack card offsets
  const scale = 1 - stackIndex * 0.04;
  const translateY = stackIndex * 10;

  return (
    <motion.div
      className={cn(
        "absolute inset-0 w-full h-full rounded-3xl bg-white card-shadow cursor-grab active:cursor-grabbing select-none",
        !isTop && "pointer-events-none"
      )}
      style={{
        x: isTop ? x : 0,
        y: isTop ? y : translateY,
        rotate: isTop ? rotate : 0,
        scale,
        zIndex: 10 - stackIndex,
      }}
      drag={isTop ? true : false}
      dragConstraints={{ left: 0, right: 0, top: 0, bottom: 0 }}
      dragElastic={0.7}
      onDragEnd={handleDragEnd}
      animate={{ scale, y: translateY }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
    >
      {/* Swipe overlays */}
      {isTop && (
        <>
          <motion.div
            style={{ opacity: applyOpacity }}
            className="absolute inset-0 rounded-3xl bg-green-400/20 border-4 border-green-400 z-10 pointer-events-none flex items-center justify-center"
          >
            <span className="text-green-600 font-black text-5xl rotate-[-20deg] border-4 border-green-600 rounded-xl px-4 py-1">
              APPLY
            </span>
          </motion.div>
          <motion.div
            style={{ opacity: skipOpacity }}
            className="absolute inset-0 rounded-3xl bg-red-400/20 border-4 border-red-400 z-10 pointer-events-none flex items-center justify-center"
          >
            <span className="text-red-500 font-black text-5xl rotate-[20deg] border-4 border-red-500 rounded-xl px-4 py-1">
              SKIP
            </span>
          </motion.div>
          <motion.div
            style={{ opacity: saveOpacity }}
            className="absolute inset-0 rounded-3xl bg-blue-400/20 border-4 border-blue-400 z-10 pointer-events-none flex items-center justify-center"
          >
            <span className="text-blue-500 font-black text-5xl border-4 border-blue-500 rounded-xl px-4 py-1">
              SAVE
            </span>
          </motion.div>
        </>
      )}

      {/* Card content */}
      <div className="h-full flex flex-col p-6 overflow-hidden">
        {/* Header: logo + company + match */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-gray-100 overflow-hidden flex items-center justify-center flex-shrink-0">
              {job.company_logo ? (
                <Image
                  src={job.company_logo}
                  alt={job.company}
                  width={56}
                  height={56}
                  className="object-contain"
                />
              ) : (
                <span className="text-2xl font-bold text-gray-400">
                  {job.company[0]}
                </span>
              )}
            </div>
            <div>
              <p className="text-sm text-gray-500 font-medium">{job.company}</p>
              <h2 className="text-xl font-bold text-gray-900 leading-tight">{job.title}</h2>
            </div>
          </div>
          {job.match_score > 0 && (
            <MatchBadge score={job.match_score} size="md" />
          )}
        </div>

        {/* Tags row */}
        <div className="flex flex-wrap gap-2 mb-4">
          {job.is_remote ? (
            <Tag icon={<Wifi className="w-3 h-3" />} label="Remote" color="blue" />
          ) : job.location ? (
            <Tag icon={<MapPin className="w-3 h-3" />} label={job.location} />
          ) : null}
          {job.job_type && (
            <Tag icon={<Briefcase className="w-3 h-3" />} label={job.job_type} />
          )}
          {(job.salary_min_lpa || job.salary_max_lpa) && (
            <Tag
              icon={<IndianRupee className="w-3 h-3" />}
              label={
                job.salary_min_lpa && job.salary_max_lpa
                  ? `${job.salary_min_lpa}–${job.salary_max_lpa} LPA`
                  : `Up to ${job.salary_max_lpa} LPA`
              }
              color="green"
            />
          )}
          {(job.experience_min !== undefined) && (
            <Tag
              icon={<Clock className="w-3 h-3" />}
              label={
                job.experience_min === 0 && job.experience_max <= 1
                  ? "Fresher"
                  : `${job.experience_min}–${job.experience_max} yrs`
              }
            />
          )}
        </div>

        {/* Skills */}
        {job.skills_required.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {job.skills_required.slice(0, 6).map((skill) => (
              <span
                key={skill}
                className="px-2.5 py-0.5 bg-brand-50 text-brand-700 rounded-full text-xs font-medium border border-brand-200"
              >
                {skill}
              </span>
            ))}
            {job.skills_required.length > 6 && (
              <span className="px-2.5 py-0.5 bg-gray-100 text-gray-500 rounded-full text-xs">
                +{job.skills_required.length - 6} more
              </span>
            )}
          </div>
        )}

        {/* Highlights */}
        {job.highlights.length > 0 && (
          <ul className="space-y-1.5 mb-4">
            {job.highlights.map((h, i) => (
              <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                <span className="mt-0.5 flex-shrink-0">•</span>
                {h}
              </li>
            ))}
          </ul>
        )}

        {/* Description preview */}
        {job.description && (
          <p className="text-sm text-gray-500 line-clamp-3 flex-1">
            {job.description}
          </p>
        )}

        {/* Footer */}
        <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between">
          <span className="text-xs text-gray-400">
            via {job.source} · {new Date(job.posted_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
          </span>
          <span className="text-xs text-gray-400">Swipe or use buttons below</span>
        </div>
      </div>
    </motion.div>
  );
}

function Tag({
  icon,
  label,
  color = "gray",
}: {
  icon: React.ReactNode;
  label: string;
  color?: "gray" | "green" | "blue";
}) {
  const colorClass =
    color === "green" ? "bg-green-50 text-green-700 border-green-200" :
    color === "blue"  ? "bg-blue-50 text-blue-700 border-blue-200" :
                        "bg-gray-50 text-gray-600 border-gray-200";
  return (
    <span className={cn("inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border", colorClass)}>
      {icon}
      {label}
    </span>
  );
}
