"use client";

import { useCallback, useState } from "react";
import { Upload, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  disabled?: boolean;
}

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

const ACCEPTED_EXTENSIONS = [".pdf", ".docx"];

/**
 * Drag-and-drop file upload zone with validation.
 */
export function FileUpload({
  onFileSelect,
  accept = ".pdf,.docx",
  disabled = false,
}: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateFile = useCallback((f: File): boolean => {
    setError(null);

    const ext = f.name.substring(f.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      setError("Only PDF and DOCX files are supported.");
      return false;
    }

    if (f.size > 10 * 1024 * 1024) {
      setError("File size must be under 10MB.");
      return false;
    }

    return true;
  }, []);

  const handleFile = useCallback(
    (f: File) => {
      if (validateFile(f)) {
        setFile(f);
        onFileSelect(f);
      }
    },
    [validateFile, onFileSelect]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      if (disabled) return;

      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) handleFile(droppedFile);
    },
    [disabled, handleFile]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const selected = e.target.files?.[0];
      if (selected) handleFile(selected);
    },
    [handleFile]
  );

  const clearFile = useCallback(() => {
    setFile(null);
    setError(null);
  }, []);

  return (
    <div className="space-y-2">
      {!file ? (
        <label
          onDragOver={(e) => {
            e.preventDefault();
            if (!disabled) setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={`
            flex flex-col items-center justify-center gap-3 p-8
            border-2 border-dashed rounded-xl cursor-pointer
            transition-all duration-200
            ${
              dragActive
                ? "border-primary bg-primary/5 scale-[1.01]"
                : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
            }
            ${disabled ? "opacity-50 cursor-not-allowed" : ""}
          `}
        >
          <div className="p-3 rounded-full bg-primary/10">
            <Upload className="h-6 w-6 text-primary" />
          </div>
          <div className="text-center">
            <p className="font-medium">
              Drop your resume here or{" "}
              <span className="text-primary underline underline-offset-4">
                browse
              </span>
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              PDF or DOCX, up to 10MB
            </p>
          </div>
          <input
            type="file"
            accept={accept}
            onChange={handleInputChange}
            className="hidden"
            disabled={disabled}
          />
        </label>
      ) : (
        <div className="flex items-center gap-3 p-4 border rounded-xl bg-muted/30">
          <div className="p-2 rounded-lg bg-primary/10">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate">{file.name}</p>
            <p className="text-xs text-muted-foreground">
              {(file.size / 1024).toFixed(1)} KB
            </p>
          </div>
          {!disabled && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0"
              onClick={clearFile}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      )}

      {error && (
        <p className="text-sm text-destructive font-medium">{error}</p>
      )}
    </div>
  );
}
