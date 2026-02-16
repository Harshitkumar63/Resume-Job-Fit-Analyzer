import { Badge } from "@/components/ui/badge";
import { Check, X } from "lucide-react";

interface SkillBadgeProps {
  skill: string;
  matched: boolean;
  score?: number;
}

/**
 * Color-coded skill badge.
 * Green with checkmark for matched skills, red with X for missing.
 */
export function SkillBadge({ skill, matched, score }: SkillBadgeProps) {
  if (matched) {
    return (
      <Badge
        variant="outline"
        className="border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 gap-1.5 py-1 px-3 text-sm font-medium"
      >
        <Check className="h-3.5 w-3.5" />
        {skill}
        {score !== undefined && (
          <span className="ml-1 text-xs opacity-70">
            {Math.round(score * 100)}%
          </span>
        )}
      </Badge>
    );
  }

  return (
    <Badge
      variant="outline"
      className="border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-400 gap-1.5 py-1 px-3 text-sm font-medium"
    >
      <X className="h-3.5 w-3.5" />
      {skill}
    </Badge>
  );
}
