/**
 * API service layer.
 *
 * Centralizes all HTTP calls to the FastAPI backend.
 * Uses axios with interceptors for consistent error handling.
 * All functions return typed responses — no `any` leaks.
 */

import axios, { AxiosError, type AxiosInstance } from "axios";
import type {
  HealthResponse,
  MatchRequest,
  MatchResult,
  UploadResponse,
} from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/**
 * Configured axios instance with base URL and timeout.
 * Timeout is generous because first request triggers model loading.
 */
const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180_000, // 3 min — model download on first call
  headers: {
    Accept: "application/json",
  },
});

/**
 * Response interceptor: unwrap axios errors into user-friendly messages.
 */
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string; message?: string }>) => {
    if (error.response) {
      const detail =
        error.response.data?.detail ||
        error.response.data?.message ||
        `Server error (${error.response.status})`;
      return Promise.reject(new Error(detail));
    }
    if (error.request) {
      return Promise.reject(
        new Error("Cannot reach the server. Is the backend running?")
      );
    }
    return Promise.reject(new Error(error.message || "Unknown error"));
  }
);

// ── API Functions ────────────────────────────────────────────

/**
 * Upload a resume file (PDF or DOCX).
 */
export async function uploadResume(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await client.post<UploadResponse>(
    "/upload_resume",
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    }
  );
  return data;
}

/**
 * Match a previously uploaded resume against a job description.
 */
export async function matchResume(
  request: MatchRequest
): Promise<MatchResult> {
  const { data } = await client.post<MatchResult>("/match", request);
  return data;
}

/**
 * Health check — verify backend is running.
 */
export async function checkHealth(): Promise<HealthResponse> {
  const { data } = await client.get<HealthResponse>("/health");
  return data;
}
