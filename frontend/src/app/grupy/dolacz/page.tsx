"use client";

/**
 * Parish group join page — /grupy/dolacz
 *
 * Priests share a short 8-char invite code (e.g. ABCD1234) with parishioners.
 * Users enter the code here to look up the group and join in one tap.
 *
 * Flow:
 *  1. Enter invite code → GET /api/v1/community/groups/code/{code}
 *  2. Preview group info (name, parish, category)
 *  3. Click "Dołącz" → POST /api/v1/community/groups/code/{code}/join
 *  4. Success — redirect to /grupy
 */

import { useState, FormEvent, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface GroupPreview {
  group_id: string;
  name: string;
  description: string | null;
  parish: string | null;
  category: string;
  member_count: number;
  is_public: boolean;
}

type Phase = "input" | "preview" | "joining" | "success" | "error";

export default function JoinByCodePage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [phase, setPhase] = useState<Phase>("input");
  const [group, setGroup] = useState<GroupPreview | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleLookup = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      const normalized = code.trim().toUpperCase();
      if (normalized.length < 4) return;
      setErrorMsg(null);

      try {
        const data = await api.get<GroupPreview>(
          `/api/v1/community/groups/code/${normalized}`
        );
        setGroup(data);
        setPhase("preview");
      } catch {
        setErrorMsg(
          "Nie znaleziono grupy o podanym kodzie. Sprawdź kod i spróbuj ponownie."
        );
      }
    },
    [code]
  );

  const handleJoin = useCallback(async () => {
    if (!group) return;
    setPhase("joining");
    try {
      await api.post(
        `/api/v1/community/groups/code/${code.trim().toUpperCase()}/join`,
        {}
      );
      setPhase("success");
      setTimeout(() => router.push("/grupy"), 2000);
    } catch (err: unknown) {
      const msg =
        err instanceof Error && err.message.includes("409")
          ? "Jesteś już członkiem tej grupy."
          : "Nie udało się dołączyć do grupy. Spróbuj ponownie.";
      setErrorMsg(msg);
      setPhase("preview");
    }
  }, [group, code, router]);

  if (phase === "input") {
    return (
      <div className="mx-auto max-w-md px-4 py-20">
        <h1 className="font-cinzel text-2xl font-bold text-sacred-text mb-2 text-center">
          Dołącz do grupy parafialnej
        </h1>
        <p className="text-gray-400 text-sm text-center mb-8">
          Wpisz 8-znakowy kod zaproszenia od swojego księdza lub lidera grupy.
        </p>

        <form onSubmit={handleLookup} className="space-y-4">
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="np. ABCD1234"
            maxLength={8}
            className="w-full text-center text-2xl font-mono tracking-widest rounded-xl border border-white/10 bg-white/5 px-4 py-4 text-sacred-text placeholder-gray-600 focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/30 uppercase"
            required
          />

          {errorMsg && (
            <p className="text-sm text-red-400 text-center">{errorMsg}</p>
          )}

          <button
            type="submit"
            disabled={code.trim().length < 4}
            className="w-full rounded-xl bg-amber-600 px-6 py-4 font-semibold text-white hover:bg-amber-700 disabled:opacity-40 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            Wyszukaj grupę
          </button>

          <p className="text-center text-xs text-gray-600">
            <Link href="/grupy" className="hover:underline text-gray-400">
              Przeglądaj wszystkie grupy
            </Link>
          </p>
        </form>
      </div>
    );
  }

  if (phase === "preview" && group) {
    return (
      <div className="mx-auto max-w-md px-4 py-20">
        <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-6 space-y-4 mb-6">
          <h2 className="font-cinzel text-xl font-semibold text-sacred-text">
            {group.name}
          </h2>
          {group.parish && (
            <p className="text-sm text-amber-400">⛪ {group.parish}</p>
          )}
          {group.description && (
            <p className="text-sm text-gray-300 leading-relaxed">
              {group.description}
            </p>
          )}
          <p className="text-xs text-gray-500">
            {group.member_count} {group.member_count === 1 ? "członek" : "członków"} ·{" "}
            {group.category}
          </p>
        </div>

        {errorMsg && (
          <p className="text-sm text-red-400 text-center mb-4">{errorMsg}</p>
        )}

        <button
          onClick={handleJoin}
          className="w-full rounded-xl bg-amber-600 px-6 py-4 font-semibold text-white hover:bg-amber-700 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-500 mb-3"
        >
          Dołącz do grupy
        </button>

        <button
          onClick={() => { setPhase("input"); setErrorMsg(null); }}
          className="w-full rounded-xl border border-white/10 px-6 py-3 text-sm text-gray-400 hover:text-gray-200 hover:border-white/20 transition-colors"
        >
          Wróć
        </button>
      </div>
    );
  }

  if (phase === "joining") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-amber-500/30 border-t-amber-500" />
        <p className="text-gray-400 text-sm">Dołączam do grupy…</p>
      </div>
    );
  }

  if (phase === "success") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center px-4">
        <div className="text-5xl">🙏</div>
        <h2 className="font-cinzel text-xl font-semibold text-sacred-text">
          Dołączyłeś/aś do grupy!
        </h2>
        <p className="text-gray-400 text-sm">
          Przekierowuję do Twoich grup…
        </p>
      </div>
    );
  }

  return null;
}
