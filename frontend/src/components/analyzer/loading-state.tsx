"use client";

import { useEffect, useState } from "react";
import { Brain, FileSearch, GitGraph, BarChart3 } from "lucide-react";

const steps = [
  { icon: FileSearch, label: "Parsing resume...", duration: 2000 },
  { icon: Brain, label: "Extracting skills with AI...", duration: 3000 },
  { icon: GitGraph, label: "Building knowledge graph...", duration: 2000 },
  { icon: BarChart3, label: "Computing fit scores...", duration: 2000 },
];

/**
 * Multi-step loading animation shown during analysis.
 * Steps auto-advance on timers to give a sense of pipeline progress.
 */
export function LoadingState() {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    if (currentStep >= steps.length - 1) return;

    const timer = setTimeout(() => {
      setCurrentStep((prev) => Math.min(prev + 1, steps.length - 1));
    }, steps[currentStep].duration);

    return () => clearTimeout(timer);
  }, [currentStep]);

  return (
    <div className="flex flex-col items-center justify-center py-16 gap-8">
      {/* Animated spinner */}
      <div className="relative">
        <div className="h-20 w-20 rounded-full border-4 border-muted animate-spin border-t-primary" />
        <div className="absolute inset-0 flex items-center justify-center">
          {(() => {
            const Icon = steps[currentStep].icon;
            return <Icon className="h-8 w-8 text-primary animate-pulse" />;
          })()}
        </div>
      </div>

      {/* Step indicators */}
      <div className="space-y-3 w-full max-w-xs">
        {steps.map((step, idx) => {
          const Icon = step.icon;
          const isActive = idx === currentStep;
          const isDone = idx < currentStep;

          return (
            <div
              key={idx}
              className={`flex items-center gap-3 text-sm transition-all duration-300 ${
                isActive
                  ? "text-foreground font-medium"
                  : isDone
                    ? "text-muted-foreground"
                    : "text-muted-foreground/40"
              }`}
            >
              <Icon className={`h-4 w-4 shrink-0 ${isActive ? "animate-pulse" : ""}`} />
              <span>{step.label}</span>
              {isDone && (
                <span className="ml-auto text-emerald-500 text-xs font-medium">
                  Done
                </span>
              )}
              {isActive && (
                <span className="ml-auto text-primary text-xs">
                  Processing...
                </span>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-sm text-muted-foreground text-center max-w-sm">
        First analysis may take 30–60 seconds while AI models load.
        <br />
        Subsequent analyses are much faster.
      </p>
    </div>
  );
}
