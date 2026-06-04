import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatLPA(value: number | null | undefined): string {
  if (!value) return "Not disclosed";
  return `₹${value} LPA`;
}

export function formatExperience(min: number, max: number): string {
  if (min === 0 && max <= 1) return "Fresher / 0–1 yr";
  return `${min}–${max} years`;
}
