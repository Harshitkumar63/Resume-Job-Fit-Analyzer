"use client";

import { useState, useCallback } from "react";
import { Navbar } from "@/components/navbar";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { FileUpload } from "@/components/analyzer/file-upload";
import { LoadingState } from "@/components/analyzer/loading-state";
import { ResultsView } from "./results-view";
import { uploadResume, matchResume } from "@/services/api";
import type {
  AnalysisState,
  UploadResponse,
  MatchResult,
} from "@/types/api";
import {
  ArrowRight,
  RotateCcw,
  AlertCircle,
  Plus,
  Minus,
} from "lucide-react";

export default function AnalyzePage() {
  // ── Form State ───────────────────────────────────────────
  const [file, setFile] = useState<File | null>(null);
  const [jobTitle, setJobTitle] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [requiredSkills, setRequiredSkills] = useState("");
  const [preferredSkills, setPreferredSkills] = useState("");
  const [minExperience, setMinExperience] = useState("");

  // ── Analysis State ───────────────────────────────────────
  const [state, setState] = useState<AnalysisState>({
    step: "upload",
    uploadResponse: null,
    matchResult: null,
    error: null,
    isLoading: false,
  });

  const parseSkills = (input: string): string[] =>
    input
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

  const isFormValid =
    file !== null &&
    jobTitle.trim().length > 0 &&
    jobDescription.trim().length >= 10;

  // ── Submit Handler ───────────────────────────────────────
  const handleAnalyze = useCallback(async () => {
    if (!file || !isFormValid) return;

    setState((prev) => ({
      ...prev,
      step: "processing",
      isLoading: true,
      error: null,
    }));

    try {
      // Step 1: Upload resume
      const uploadResp: UploadResponse = await uploadResume(file);

      // Step 2: Match against JD
      const matchResp: MatchResult = await matchResume({
        resume_id: uploadResp.resume_id,
        job_description: {
          title: jobTitle.trim(),
          description: jobDescription.trim(),
          required_skills: parseSkills(requiredSkills),
          preferred_skills: parseSkills(preferredSkills),
          min_experience_years: minExperience
            ? parseFloat(minExperience)
            : null,
        },
      });

      setState({
        step: "results",
        uploadResponse: uploadResp,
        matchResult: matchResp,
        error: null,
        isLoading: false,
      });
    } catch (err) {
      setState((prev) => ({
        ...prev,
        step: "upload",
        isLoading: false,
        error: err instanceof Error ? err.message : "Analysis failed",
      }));
    }
  }, [
    file,
    isFormValid,
    jobTitle,
    jobDescription,
    requiredSkills,
    preferredSkills,
    minExperience,
  ]);

  // ── Reset ────────────────────────────────────────────────
  const handleReset = useCallback(() => {
    setFile(null);
    setJobTitle("");
    setJobDescription("");
    setRequiredSkills("");
    setPreferredSkills("");
    setMinExperience("");
    setState({
      step: "upload",
      uploadResponse: null,
      matchResult: null,
      error: null,
      isLoading: false,
    });
  }, []);

  // ── Render: Loading ──────────────────────────────────────
  if (state.step === "processing") {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 container mx-auto px-4 md:px-6 py-12">
          <Card className="max-w-2xl mx-auto">
            <CardHeader className="text-center">
              <CardTitle className="text-2xl">Analyzing Resume</CardTitle>
              <CardDescription>
                Running the multi-stage AI pipeline...
              </CardDescription>
            </CardHeader>
            <CardContent>
              <LoadingState />
            </CardContent>
          </Card>
        </main>
      </div>
    );
  }

  // ── Render: Results ──────────────────────────────────────
  if (state.step === "results" && state.matchResult && state.uploadResponse) {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 container mx-auto px-4 md:px-6 py-8">
          <div className="max-w-5xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold">Analysis Results</h1>
                <p className="text-muted-foreground text-sm mt-1">
                  {state.uploadResponse.filename} &rarr;{" "}
                  {state.matchResult.job_title}
                </p>
              </div>
              <Button variant="outline" onClick={handleReset}>
                <RotateCcw className="h-4 w-4 mr-2" />
                New Analysis
              </Button>
            </div>
            <ResultsView
              result={state.matchResult}
              upload={state.uploadResponse}
            />
          </div>
        </main>
      </div>
    );
  }

  // ── Render: Upload Form ──────────────────────────────────
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 container mx-auto px-4 md:px-6 py-8 md:py-12">
        <div className="max-w-3xl mx-auto space-y-8">
          {/* Header */}
          <div className="text-center space-y-2">
            <h1 className="text-3xl font-bold">Analyze Resume Fit</h1>
            <p className="text-muted-foreground">
              Upload a resume and describe the job to get an AI-powered fit
              analysis.
            </p>
          </div>

          {/* Error Banner */}
          {state.error && (
            <div className="flex items-start gap-3 p-4 rounded-lg border border-destructive/50 bg-destructive/10 text-destructive">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Analysis Failed</p>
                <p className="text-sm mt-1 opacity-90">{state.error}</p>
              </div>
            </div>
          )}

          {/* Resume Upload */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">1. Upload Resume</CardTitle>
              <CardDescription>
                Upload a PDF or DOCX resume file.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FileUpload
                onFileSelect={setFile}
                disabled={state.isLoading}
              />
            </CardContent>
          </Card>

          {/* Job Description */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">
                2. Job Description
              </CardTitle>
              <CardDescription>
                Describe the role and required skills.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Job Title */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Job Title <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Senior ML Engineer"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Job Description <span className="text-destructive">*</span>
                </label>
                <Textarea
                  placeholder="Paste the full job description here..."
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  rows={6}
                  className="resize-y"
                />
              </div>

              <Separator />

              {/* Required Skills */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Required Skills
                </label>
                <input
                  type="text"
                  placeholder="e.g. Python, PyTorch, Machine Learning, Docker"
                  value={requiredSkills}
                  onChange={(e) => setRequiredSkills(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                />
                <p className="text-xs text-muted-foreground">
                  Comma-separated list of must-have skills
                </p>
              </div>

              {/* Preferred Skills */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Preferred Skills
                </label>
                <input
                  type="text"
                  placeholder="e.g. Kubernetes, TensorFlow, MLOps"
                  value={preferredSkills}
                  onChange={(e) => setPreferredSkills(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                />
                <p className="text-xs text-muted-foreground">
                  Comma-separated list of nice-to-have skills
                </p>
              </div>

              {/* Min Experience */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Minimum Experience (years)
                </label>
                <input
                  type="number"
                  placeholder="e.g. 3"
                  min="0"
                  step="0.5"
                  value={minExperience}
                  onChange={(e) => setMinExperience(e.target.value)}
                  className="flex h-10 w-32 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                />
              </div>
            </CardContent>
          </Card>

          {/* Submit */}
          <Button
            size="lg"
            className="w-full text-base"
            disabled={!isFormValid || state.isLoading}
            onClick={handleAnalyze}
          >
            Analyze Fit
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </main>
    </div>
  );
}
