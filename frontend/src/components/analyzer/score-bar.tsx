"use client";

import { useEffect, useState } from "react";

interface ScoreBarProps {
  label: string;
  score: number; // 0–1
  weight: number; // 0–1
  delay?: number; // animation delay in ms
}

/**
 * Horizontal score bar with animated fill and weight indicator.
 * Used in the score breakdown section.
 */
export function ScoreBar({ label, score, weight, delay = 0 }: ScoreBarProps) {
  const [animatedWidth, setAnimatedWidth] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedWidth(score * 100), 100 + delay);
    return () => clearTimeout(timer);
  }, [score, delay]);

  const getBarColor = (s: number): string => {
    if (s >= 0.75) return "bg-emerald-500";
    if (s >= 0.5) return "bg-amber-500";
    if (s >= 0.25) return "bg-orange-500";
    return "bg-red-500";
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <div className="flex items-center gap-3">
          <span className="text-muted-foreground text-xs">
            weight: {Math.round(weight * 100)}%
          </span>
          <span className="font-semibold tabular-nums w-12 text-right">
            {Math.round(score * 100)}%
          </span>
        </div>
      </div>
      <div className="h-2.5 w-full rounded-full bg-muted/50 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ease-out ${getBarColor(score)}`}
          style={{ width: `${animatedWidth}%` }}
        />
      </div>
    </div>
  );
}
