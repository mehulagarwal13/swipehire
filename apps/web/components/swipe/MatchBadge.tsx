import { cn } from "@/lib/utils";

interface MatchBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export function MatchBadge({ score, size = "md", showLabel = true }: MatchBadgeProps) {
  const color =
    score >= 80 ? "bg-green-500 text-white" :
    score >= 60 ? "bg-yellow-400 text-gray-900" :
                  "bg-gray-300 text-gray-700";

  const sizeClass =
    size === "sm" ? "text-xs px-2 py-0.5" :
    size === "lg" ? "text-base px-4 py-1.5" :
                    "text-sm px-3 py-1";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-semibold",
        color,
        sizeClass
      )}
      title={`${score}% match score`}
    >
      {score >= 80 && <span>🎯</span>}
      {score}%{showLabel && " match"}
    </span>
  );
}
