"use client";

import { useEffect, useState } from "react";

interface ScoreCircleProps {
  score: number; // 0–1
  label: string;
  size?: number;
  strokeWidth?: number;
}

/**
 * Animated circular progress indicator for fit scores.
 *
 * Uses SVG with stroke-dasharray animation.
 * Color transitions from red → amber → green based on score.
 */
export function ScoreCircle({
  score,
  label,
  size = 200,
  strokeWidth = 12,
}: ScoreCircleProps) {
  const [animatedScore, setAnimatedScore] = useState(0);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - animatedScore * circumference;

  // Animate on mount
  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(score), 100);
    return () => clearTimeout(timer);
  }, [score]);

  const getColor = (s: number): string => {
    if (s >= 0.75) return "text-emerald-500";
    if (s >= 0.5) return "text-amber-500";
    if (s >= 0.25) return "text-orange-500";
    return "text-red-500";
  };

  const getStrokeColor = (s: number): string => {
    if (s >= 0.75) return "#10b981";
    if (s >= 0.5) return "#f59e0b";
    if (s >= 0.25) return "#f97316";
    return "#ef4444";
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          className="-rotate-90"
          viewBox={`0 0 ${size} ${size}`}
        >
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-muted/30"
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={getStrokeColor(score)}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-4xl font-bold ${getColor(score)}`}>
            {Math.round(animatedScore * 100)}%
          </span>
          <span className="text-sm text-muted-foreground mt-1">{label}</span>
        </div>
      </div>
    </div>
  );
}
