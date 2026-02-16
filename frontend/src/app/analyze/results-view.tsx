"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { ScoreCircle } from "@/components/analyzer/score-circle";
import { ScoreBar } from "@/components/analyzer/score-bar";
import { SkillBadge } from "@/components/analyzer/skill-badge";
import { FitLabel } from "@/components/analyzer/fit-label";
import {
  ChevronDown,
  ChevronUp,
  FileText,
  Target,
  BrainCircuit,
  Layers,
} from "lucide-react";
import type { MatchResult, UploadResponse } from "@/types/api";

interface ResultsViewProps {
  result: MatchResult;
  upload: UploadResponse;
}

export function ResultsView({ result, upload }: ResultsViewProps) {
  const [showExplanation, setShowExplanation] = useState(false);

  const bd = result.score_breakdown;
  const matchedCount = result.matched_skills.length;
  const missingCount = result.missing_skills.length;
  const totalSkills = matchedCount + missingCount;
  const coveragePercent =
    totalSkills > 0 ? Math.round((matchedCount / totalSkills) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* ── Top Row: Score + Summary ────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Overall Score */}
        <Card className="lg:col-span-1">
          <CardContent className="flex flex-col items-center justify-center py-8">
            <ScoreCircle
              score={result.overall_score}
              label={result.fit_label}
            />
            <div className="mt-4">
              <FitLabel label={result.fit_label} />
            </div>
          </CardContent>
        </Card>

        {/* Score Breakdown */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Layers className="h-5 w-5 text-primary" />
              Score Breakdown
            </CardTitle>
            <CardDescription>
              Three independent scoring dimensions combined with configurable
              weights.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <ScoreBar
              label="Semantic Similarity"
              score={bd.semantic_score}
              weight={bd.semantic_weight}
              delay={0}
            />
            <ScoreBar
              label="Graph Structure"
              score={bd.graph_score}
              weight={bd.graph_weight}
              delay={200}
            />
            <ScoreBar
              label="Experience Fit"
              score={bd.experience_score}
              weight={bd.experience_weight}
              delay={400}
            />
          </CardContent>
        </Card>
      </div>

      {/* ── Stats Cards ─────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={<FileText className="h-4 w-4" />}
          label="Skills Found"
          value={upload.skill_count.toString()}
        />
        <StatCard
          icon={<Target className="h-4 w-4" />}
          label="Skills Matched"
          value={`${matchedCount}/${totalSkills}`}
        />
        <StatCard
          icon={<BrainCircuit className="h-4 w-4" />}
          label="Coverage"
          value={`${coveragePercent}%`}
        />
        <StatCard
          icon={<Layers className="h-4 w-4" />}
          label="Experience"
          value={
            upload.experience_years
              ? `${upload.experience_years} yrs`
              : "N/A"
          }
        />
      </div>

      {/* ── Matched Skills ──────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Matched Skills</CardTitle>
          <CardDescription>
            Skills from your resume that match the job requirements.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {result.matched_skills.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {result.matched_skills
                .sort((a, b) => b.similarity_score - a.similarity_score)
                .map((skill) => (
                  <SkillBadge
                    key={skill.skill}
                    skill={skill.skill}
                    matched={true}
                    score={skill.similarity_score}
                  />
                ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No direct skill matches found.
            </p>
          )}
        </CardContent>
      </Card>

      {/* ── Missing Skills ──────────────────────────────────── */}
      {result.missing_skills.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Missing Skills</CardTitle>
            <CardDescription>
              Job requirements not found in your resume.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {result.missing_skills.map((skill) => (
                <SkillBadge key={skill} skill={skill} matched={false} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Explanation (Collapsible) ───────────────────────── */}
      <Card>
        <CardHeader
          className="cursor-pointer"
          onClick={() => setShowExplanation(!showExplanation)}
        >
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">Detailed Explanation</CardTitle>
              <CardDescription>
                Full AI-generated analysis breakdown.
              </CardDescription>
            </div>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              {showExplanation ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </div>
        </CardHeader>
        {showExplanation && (
          <CardContent>
            <Separator className="mb-4" />
            <pre className="whitespace-pre-wrap text-sm font-mono leading-relaxed text-muted-foreground bg-muted/30 rounded-lg p-4 overflow-x-auto">
              {result.explanation}
            </pre>
          </CardContent>
        )}
      </Card>
    </div>
  );
}

// ── Helper Component ─────────────────────────────────────────

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-5 gap-1">
        <div className="text-muted-foreground">{icon}</div>
        <span className="text-2xl font-bold">{value}</span>
        <span className="text-xs text-muted-foreground">{label}</span>
      </CardContent>
    </Card>
  );
}
