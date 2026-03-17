"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Sparkles, LogIn } from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import { useToast } from "@/components/ui/toast";
import { LoadingSpinner } from "@/components/ui/loading";

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading } = useAuthStore();
  const toast = useToast();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    try {
      await login(email, password);
      toast.success("Zalogowano pomyślnie");
      router.push("/dashboard");
    } catch {
      toast.error("Nieprawidłowy email lub hasło");
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-4">
      <div className="w-full max-w-md animate-fade-in">
        {/* Header */}
        <div className="mb-8 text-center">
          <Sparkles className="mx-auto mb-4 h-10 w-10 text-gold glow-gold-text" />
          <h1 className="font-heading text-3xl text-gold">Zaloguj się</h1>
          <p className="mt-2 text-sacred-text-muted">
            Wejdź do swojej przestrzeni duchowej
          </p>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="space-y-5 rounded-xl border border-sacred-border bg-sacred-surface p-8"
        >
          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-sm font-medium text-parchment"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="twoj@email.pl"
              className="w-full rounded-lg border border-sacred-border bg-sacred-bg px-4 py-2.5 text-sacred-text placeholder:text-sacred-text-muted/50 focus:border-gold focus:outline-none focus:ring-1 focus:ring-gold"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-1.5 block text-sm font-medium text-parchment"
            >
              Hasło
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Twoje hasło"
              className="w-full rounded-lg border border-sacred-border bg-sacred-bg px-4 py-2.5 text-sacred-text placeholder:text-sacred-text-muted/50 focus:border-gold focus:outline-none focus:ring-1 focus:ring-gold"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-gold px-4 py-2.5 font-medium text-ink transition-all hover:bg-gold-light disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <LoadingSpinner size="sm" />
            ) : (
              <>
                <LogIn className="h-4 w-4" />
                Zaloguj się
              </>
            )}
          </button>
        </form>

        {/* Register link */}
        <p className="mt-6 text-center text-sm text-sacred-text-muted">
          Nie masz konta?{" "}
          <Link
            href="/auth/register"
            className="text-gold transition-colors hover:text-gold-light"
          >
            Zarejestruj się
          </Link>
        </p>
      </div>
    </div>
  );
}
