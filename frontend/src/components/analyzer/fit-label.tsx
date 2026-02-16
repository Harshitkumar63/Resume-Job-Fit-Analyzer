import { Badge } from "@/components/ui/badge";
import { Sparkles, TrendingUp, Minus, TrendingDown } from "lucide-react";

interface FitLabelProps {
  label: string;
}

const labelConfig: Record<
  string,
  { color: string; icon: React.ReactNode }
> = {
  "Strong Fit": {
    color:
      "border-emerald-500/40 bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
    icon: <Sparkles className="h-3.5 w-3.5" />,
  },
  "Moderate Fit": {
    color:
      "border-amber-500/40 bg-amber-500/15 text-amber-700 dark:text-amber-400",
    icon: <TrendingUp className="h-3.5 w-3.5" />,
  },
  "Potential Fit": {
    color:
      "border-orange-500/40 bg-orange-500/15 text-orange-700 dark:text-orange-400",
    icon: <Minus className="h-3.5 w-3.5" />,
  },
  "Weak Fit": {
    color: "border-red-500/40 bg-red-500/15 text-red-700 dark:text-red-400",
    icon: <TrendingDown className="h-3.5 w-3.5" />,
  },
};

/**
 * Styled fit label badge with contextual color and icon.
 */
export function FitLabel({ label }: FitLabelProps) {
  const config = labelConfig[label] || labelConfig["Weak Fit"];

  return (
    <Badge
      variant="outline"
      className={`${config.color} gap-1.5 py-1.5 px-4 text-sm font-semibold`}
    >
      {config.icon}
      {label}
    </Badge>
  );
}
