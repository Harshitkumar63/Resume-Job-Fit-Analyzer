"use client";

import Link from "next/link";
import { Brain } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-sm">
      <div className="container mx-auto flex h-14 items-center justify-between px-4 md:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <Brain className="h-5 w-5 text-primary" />
          <span className="hidden sm:inline">Resume Fit Analyzer</span>
        </Link>

        <nav className="flex items-center gap-1">
          <Link
            href="/analyze"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors px-3 py-2 rounded-md hover:bg-muted"
          >
            Analyze
          </Link>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
