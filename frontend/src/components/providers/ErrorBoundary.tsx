"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";
import Link from "next/link";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center px-4 text-center">
          <div className="mb-4 text-4xl">✝</div>
          <h2 className="mb-2 font-heading text-xl text-[--color-gold]">
            Coś poszło nie tak
          </h2>
          <p className="mb-6 max-w-sm text-sm text-[--color-sacred-text-muted]/70">
            Wystąpił nieoczekiwany błąd. Odśwież stronę lub wróć do ekranu głównego.
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="rounded-lg border border-[--color-gold]/40 bg-[--color-gold]/10 px-5 py-2 text-sm text-[--color-gold] transition-all hover:bg-[--color-gold]/20"
            >
              Spróbuj ponownie
            </button>
            <Link
              href="/"
              className="rounded-lg border border-[--color-sacred-border] px-5 py-2 text-sm text-[--color-sacred-text-muted] transition-all hover:border-[--color-gold]/30"
            >
              Strona główna
            </Link>
          </div>
          {process.env.NODE_ENV === "development" && this.state.error && (
            <pre className="mt-6 max-w-lg overflow-auto rounded-lg bg-black/40 p-4 text-left text-xs text-red-400">
              {this.state.error.message}
            </pre>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
