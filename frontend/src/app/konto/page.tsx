"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/stores/auth";
import { useBillingStore } from "@/stores/billing";
import { api } from "@/lib/api";

interface FullProfile {
  id: string;
  email: string;
  display_name: string;
  role: string;
  subscription_tier: string;
  created_at?: string;
}

interface PrivacySettings {
  journal_is_private: boolean;
  ai_can_read_journal: boolean;
  ai_history_enabled: boolean;
  preferred_language: string;
  spiritual_tradition: string;
}

const TIER_LABEL: Record<string, string> = {
  free:     "Bezpłatny",
  pilgrim:  "Pielgrzym (miesięczny)",
  disciple: "Uczeń (roczny)",
  mystic:   "Mistyk",
};

const TIER_COLOR: Record<string, string> = {
  free:     "text-gray-400",
  pilgrim:  "text-[#d4af37]",
  disciple: "text-[#d4af37]",
  mystic:   "text-purple-400",
};

const ROLE_LABEL: Record<string, string> = {
  user:        "Użytkownik",
  premium_user:"Premium",
  moderator:   "Moderator",
  admin:       "Administrator",
};

export default function KontoPage() {
  const router = useRouter();
  const { user, logout, isAuthenticated, loadFromStorage } = useAuthStore();
  const { subscription, fetchStatus, openPortal, loading: billingLoading } = useBillingStore();

  const [profile, setProfile] = useState<FullProfile | null>(null);
  const [editName, setEditName] = useState("");
  const [editingName, setEditingName] = useState(false);
  const [savingName, setSavingName] = useState(false);
  const [profileLoading, setProfileLoading] = useState(true);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const [privacy, setPrivacy] = useState<PrivacySettings | null>(null);
  const [savingPrivacy, setSavingPrivacy] = useState(false);

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  useEffect(() => {
    if (!isAuthenticated) { router.push("/auth/login"); return; }
    Promise.all([
      api.get<FullProfile>("/api/v1/users/me/profile")
        .then((p) => { setProfile(p); setEditName(p.display_name); setProfileLoading(false); })
        .catch(() => setProfileLoading(false)),
      api.get<PrivacySettings>("/api/v1/users/me/privacy")
        .then(setPrivacy)
        .catch(() => {}),
      fetchStatus(),
    ]);
  }, [isAuthenticated, router, fetchStatus]);

  const saveName = async () => {
    if (!editName.trim() || editName === profile?.display_name) { setEditingName(false); return; }
    setSavingName(true);
    try {
      const updated = await api.put<FullProfile>("/api/v1/users/me/profile", { display_name: editName.trim() });
      setProfile(updated);
      setEditingName(false);
    } catch { /* ignore */ } finally { setSavingName(false); }
  };

  const updatePrivacy = async (patch: Partial<PrivacySettings>) => {
    if (!privacy) return;
    const optimistic = { ...privacy, ...patch };
    setPrivacy(optimistic);
    setSavingPrivacy(true);
    try {
      const updated = await api.put<PrivacySettings>("/api/v1/users/me/privacy", patch);
      setPrivacy(updated);
    } catch {
      setPrivacy(privacy);
    } finally {
      setSavingPrivacy(false);
    }
  };

  const handleLogout = () => { logout(); router.push("/"); };

  const handleDeleteRequest = async () => {
    try {
      await api.post("/api/v1/users/me/delete", {});
      handleLogout();
    } catch { /* ignore */ }
  };

  if (profileLoading) {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white flex items-center justify-center">
        <div className="animate-pulse text-[#d4af37] text-2xl">✝</div>
      </main>
    );
  }

  const isPremium = subscription?.is_premium ?? false;
  const tier = profile?.subscription_tier ?? "free";
  const initials = (profile?.display_name ?? user?.displayName ?? "?")
    .split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

  const joinedDate = profile?.created_at
    ? new Date(profile.created_at).toLocaleDateString("pl-PL", { month: "long", year: "numeric" })
    : null;

  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white">
      <div className="max-w-2xl mx-auto px-4 py-10 pb-28">

        {/* Avatar + name */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 rounded-full bg-[#d4af37]/20 border-2 border-[#d4af37]/40 flex items-center justify-center text-2xl font-bold text-[#d4af37] mx-auto mb-4">
            {initials}
          </div>
          {editingName ? (
            <div className="flex items-center justify-center gap-2">
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") saveName(); if (e.key === "Escape") setEditingName(false); }}
                autoFocus
                className="bg-white/10 border border-white/20 rounded-xl px-4 py-2 text-lg font-semibold text-center text-white focus:outline-none focus:border-[#d4af37] w-52"
              />
              <button onClick={saveName} disabled={savingName} className="text-[#d4af37] hover:text-white transition-colors text-sm">
                {savingName ? "…" : "✓"}
              </button>
              <button onClick={() => setEditingName(false)} className="text-gray-500 hover:text-white transition-colors text-sm">✕</button>
            </div>
          ) : (
            <button onClick={() => setEditingName(true)} className="group flex items-center gap-2 mx-auto">
              <h1 className="text-xl font-bold text-white">{profile?.display_name ?? user?.displayName}</h1>
              <span className="text-gray-600 text-xs group-hover:text-[#d4af37] transition-colors">✏</span>
            </button>
          )}
          <p className="text-gray-500 text-sm mt-1">{profile?.email}</p>
          {joinedDate && <p className="text-gray-700 text-xs mt-0.5">W Sancta Nexus od {joinedDate}</p>}
        </div>

        {/* Subscription card */}
        <div className={`rounded-2xl border p-5 mb-4 ${
          isPremium
            ? "bg-[#d4af37]/10 border-[#d4af37]/40"
            : "bg-white/5 border-white/10"
        }`}>
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-xs text-gray-500 mb-0.5">Twój plan</div>
              <div className={`font-semibold text-lg ${TIER_COLOR[tier] ?? "text-gray-300"}`}>
                {TIER_LABEL[tier] ?? tier}
              </div>
            </div>
            {isPremium && (
              <span className="text-xs bg-[#d4af37] text-black font-bold px-2 py-1 rounded-full">PREMIUM</span>
            )}
          </div>

          {isPremium && subscription?.current_period_end && (
            <p className="text-xs text-gray-500 mb-3">
              {subscription.cancel_at_period_end ? "Wygasa" : "Odnawia się"}{" "}
              {new Date(subscription.current_period_end).toLocaleDateString("pl-PL", { day: "numeric", month: "long", year: "numeric" })}
            </p>
          )}

          {isPremium ? (
            <button
              onClick={() => openPortal()}
              disabled={billingLoading}
              className="w-full text-sm text-gray-300 hover:text-white py-2 border border-white/10 hover:border-white/30 rounded-xl transition-colors"
            >
              {billingLoading ? "Ładowanie…" : "Zarządzaj subskrypcją → Stripe Portal"}
            </button>
          ) : (
            <Link
              href="/cennik"
              className="block w-full text-center bg-[#d4af37] text-black font-semibold py-2.5 rounded-xl hover:bg-[#c9a227] transition-colors text-sm"
            >
              Odblokuj Premium →
            </Link>
          )}
        </div>

        {/* Role badge (for moderators/admins) */}
        {profile?.role && !["user", "premium_user"].includes(profile.role) && (
          <div className="bg-purple-900/20 border border-purple-700/30 rounded-xl p-3 mb-4 flex items-center gap-2">
            <span className="text-purple-400 text-sm">⚑</span>
            <span className="text-sm text-purple-300">{ROLE_LABEL[profile.role] ?? profile.role}</span>
            {profile.role === "admin" && (
              <Link href="/admin" className="ml-auto text-xs text-purple-400 hover:text-purple-200">Panel admina →</Link>
            )}
          </div>
        )}

        {/* Quick links */}
        <div className="space-y-2 mb-6">
          <h3 className="text-xs text-gray-600 uppercase tracking-wider mb-2">Moje rzeczy</h3>
          {[
            { label: "Dziennik duchowy", href: "/dziennik", icon: "📓" },
            { label: "Historia Lectio Divina", href: "/lectio-divina/historia", icon: "📖" },
            { label: "Moje intencje modlitewne", href: "/intencje", icon: "🙏" },
            { label: "Nowenny", href: "/nowenna", icon: "📿" },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl p-3 transition-all"
            >
              <span className="text-xl">{item.icon}</span>
              <span className="text-sm text-white">{item.label}</span>
              <span className="ml-auto text-gray-600 text-xs">→</span>
            </Link>
          ))}
        </div>

        {/* Privacy settings */}
        {privacy && (
          <div className="mb-6">
            <h3 className="text-xs text-gray-600 uppercase tracking-wider mb-3">
              Prywatność i AI
              {savingPrivacy && <span className="ml-2 text-[#d4af37] animate-pulse">…</span>}
            </h3>
            <div className="space-y-2">
              {[
                {
                  key: "journal_is_private" as const,
                  label: "Dziennik prywatny",
                  desc: "Wpisy widoczne tylko dla Ciebie",
                  icon: "🔒",
                },
                {
                  key: "ai_can_read_journal" as const,
                  label: "AI może czytać dziennik",
                  desc: "Umożliwia personalizowane wskazówki i spostrzeżenia",
                  icon: "🤖",
                },
                {
                  key: "ai_history_enabled" as const,
                  label: "Historia interakcji z AI",
                  desc: "Zapisuje metadane do analizy wzorców",
                  icon: "📊",
                },
              ].map(({ key, label, desc, icon }) => (
                <button
                  key={key}
                  onClick={() => updatePrivacy({ [key]: !privacy[key] })}
                  disabled={savingPrivacy}
                  className="w-full flex items-center gap-3 bg-white/5 hover:bg-white/8 border border-white/10 rounded-xl p-3 text-left transition-all disabled:opacity-60"
                >
                  <span className="text-xl">{icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-white">{label}</div>
                    <div className="text-xs text-gray-500">{desc}</div>
                  </div>
                  <div className={`w-10 h-5 rounded-full transition-colors flex-shrink-0 ${privacy[key] ? "bg-[#d4af37]" : "bg-white/10"}`}>
                    <div className={`w-4 h-4 rounded-full bg-white shadow m-0.5 transition-transform ${privacy[key] ? "translate-x-5" : "translate-x-0"}`} />
                  </div>
                </button>
              ))}

              {/* Spiritual tradition */}
              <div className="bg-white/5 border border-white/10 rounded-xl p-3">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-xl">⛪</span>
                  <div>
                    <div className="text-sm font-medium text-white">Tradycja duchowa</div>
                    <div className="text-xs text-gray-500">Dostosowuje styl medytacji i modlitwy</div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {[
                    { id: "ignatian", label: "Ignacjańska" },
                    { id: "benedictine", label: "Benedyktyńska" },
                    { id: "carmelite", label: "Karmelitańska" },
                    { id: "franciscan", label: "Franciszkańska" },
                    { id: "dominican", label: "Dominikańska" },
                  ].map((t) => (
                    <button
                      key={t.id}
                      onClick={() => updatePrivacy({ spiritual_tradition: t.id })}
                      disabled={savingPrivacy}
                      className={`text-xs px-3 py-1.5 rounded-full border transition-all ${
                        privacy.spiritual_tradition === t.id
                          ? "bg-[#d4af37] border-[#d4af37] text-black font-semibold"
                          : "bg-white/5 border-white/10 text-gray-400 hover:border-white/30"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Data export */}
        <div className="space-y-2 mb-6">
          <h3 className="text-xs text-gray-600 uppercase tracking-wider mb-2">Moje dane (RODO)</h3>
          <a
            href="/api/v1/users/me/export"
            className="flex items-center gap-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl p-3 transition-all"
          >
            <span className="text-xl">📦</span>
            <span className="text-sm text-white">Pobierz moje dane (JSON)</span>
          </a>
        </div>

        {/* Logout + delete */}
        <div className="space-y-3">
          <button
            onClick={handleLogout}
            className="w-full bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl p-3 text-sm text-gray-300 hover:text-white transition-all"
          >
            Wyloguj się
          </button>

          {!showDeleteConfirm ? (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="w-full text-xs text-gray-700 hover:text-red-400 transition-colors py-2"
            >
              Usuń konto
            </button>
          ) : (
            <div className="bg-red-900/20 border border-red-700/30 rounded-2xl p-4">
              <p className="text-sm text-red-300 mb-3 text-center">
                Czy na pewno chcesz usunąć konto? Tej operacji nie można cofnąć.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 py-2 text-sm text-gray-400 border border-white/10 rounded-xl hover:border-white/30 transition-colors"
                >
                  Anuluj
                </button>
                <button
                  onClick={handleDeleteRequest}
                  className="flex-1 py-2 text-sm text-red-300 border border-red-700/40 rounded-xl hover:bg-red-900/30 transition-colors"
                >
                  Usuń bezpowrotnie
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
