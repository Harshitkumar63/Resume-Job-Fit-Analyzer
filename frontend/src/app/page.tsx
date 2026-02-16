import Link from "next/link";
import { ArrowRight, Brain, GitGraph, BarChart3, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Navbar } from "@/components/navbar";

const features = [
  {
    icon: Brain,
    title: "Transformer NER",
    description:
      "BERT-based named entity recognition extracts skills beyond simple keyword matching.",
  },
  {
    icon: GitGraph,
    title: "Knowledge Graph",
    description:
      "Skill ontology with category relationships powers structural similarity scoring.",
  },
  {
    icon: BarChart3,
    title: "Hybrid Scoring",
    description:
      "Combines semantic similarity, graph overlap, and experience fit into one score.",
  },
  {
    icon: Shield,
    title: "Explainable AI",
    description:
      "Every score is broken down — matched skills, missing skills, and contribution weights.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1">
        {/* Hero */}
        <section className="container mx-auto px-4 md:px-6 py-20 md:py-32">
          <div className="max-w-3xl mx-auto text-center space-y-8">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border bg-muted/50 text-sm text-muted-foreground">
              <Brain className="h-4 w-4 text-primary" />
              Powered by Transformers + FAISS + Knowledge Graphs
            </div>

            <h1 className="text-4xl md:text-6xl font-bold tracking-tight leading-tight">
              AI Resume–Job
              <br />
              <span className="text-primary">Fit Analyzer</span>
            </h1>

            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
              Go beyond keyword matching. Upload your resume, paste a job
              description, and get an explainable fit score powered by
              transformer-based skill extraction and graph reasoning.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button asChild size="lg" className="text-base px-8">
                <Link href="/analyze">
                  Start Matching
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button
                asChild
                variant="outline"
                size="lg"
                className="text-base px-8"
              >
                <a
                  href="http://localhost:8000/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  API Docs
                </a>
              </Button>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="border-t bg-muted/30">
          <div className="container mx-auto px-4 md:px-6 py-20">
            <h2 className="text-2xl md:text-3xl font-bold text-center mb-12">
              How It Works
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {features.map((feature) => (
                <div
                  key={feature.title}
                  className="p-6 rounded-xl border bg-card hover:shadow-md transition-shadow"
                >
                  <div className="p-2.5 rounded-lg bg-primary/10 w-fit mb-4">
                    <feature.icon className="h-5 w-5 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-2">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pipeline Diagram */}
        <section className="container mx-auto px-4 md:px-6 py-20">
          <div className="max-w-3xl mx-auto text-center space-y-8">
            <h2 className="text-2xl md:text-3xl font-bold">
              Multi-Stage Pipeline
            </h2>
            <div className="flex flex-wrap items-center justify-center gap-3 text-sm">
              {[
                "Resume Upload",
                "Text Extraction",
                "NER Skill Extraction",
                "Ontology Normalization",
                "FAISS Vector Search",
                "Graph Reasoning",
                "Hybrid Scoring",
                "Explainable Result",
              ].map((step, idx) => (
                <div key={step} className="flex items-center gap-3">
                  <span className="px-3 py-1.5 rounded-lg border bg-card font-medium">
                    {step}
                  </span>
                  {idx < 7 && (
                    <ArrowRight className="h-4 w-4 text-muted-foreground hidden sm:block" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t py-6">
        <div className="container mx-auto px-4 md:px-6 text-center text-sm text-muted-foreground">
          Built with FastAPI + PyTorch + FAISS + Next.js
        </div>
      </footer>
    </div>
  );
}
