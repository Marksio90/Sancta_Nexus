"use client";

import { useState, useEffect, useCallback } from "react";
import { api, ApiError } from "@/lib/api";
import {
  Users,
  ShieldAlert,
  FileText,
  Activity,
  CheckCircle,
  XCircle,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";

// ── Typy ─────────────────────────────────────────────────────────────────────

interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: string;
  subscription_tier: string;
  is_active: boolean;
  created_at: string;
  deleted_at: string | null;
}

interface Intention {
  id: string;
  content: string;
  user_id: string | null;
  status: string;
  created_at: string;
}

interface AiInteraction {
  id: string;
  user_id: string | null;
  module: string;
  risk_category: string;
  was_modified: boolean;
  violations: string | null;
  created_at: string;
}

interface AuditLog {
  id: string;
  event_type: string;
  user_id: string | null;
  actor_id: string | null;
  description: string;
  created_at: string;
}

type Tab = "users" | "intentions" | "safety" | "logs";

const TAB_CONFIG = [
  { id: "users" as Tab, label: "Użytkownicy", icon: Users },
  { id: "intentions" as Tab, label: "Intencje", icon: FileText },
  { id: "safety" as Tab, label: "AI Safety", icon: ShieldAlert },
  { id: "logs" as Tab, label: "Logi audytu", icon: Activity },
];

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-red-800/40 text-red-300",
  moderator: "bg-orange-800/40 text-orange-300",
  user: "bg-blue-800/40 text-blue-300",
};

const RISK_COLORS: Record<string, string> = {
  safe: "bg-green-800/40 text-green-300",
  low: "bg-yellow-800/40 text-yellow-300",
  medium: "bg-orange-800/40 text-orange-300",
  high: "bg-red-800/40 text-red-300",
  crisis: "bg-red-900/60 text-red-200 font-bold",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("pl-PL", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Panel użytkowników ────────────────────────────────────────────────────────

function UsersPanel() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [changingRole, setChangingRole] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = { page: String(page), page_size: "30" };
      if (roleFilter) params.role = roleFilter;
      const data = await api.get<{ users: AdminUser[]; total: number }>("/api/v1/admin/users", { params });
      setUsers(data.users);
      setTotal(data.total);
    } catch {
      setUsers([]);
    } finally {
      setLoading(false);
    }
  }, [page, roleFilter]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { loadUsers(); }, [loadUsers]);

  const changeRole = async (userId: string, newRole: string) => {
    setChangingRole(userId);
    try {
      await api.put(`/api/v1/admin/users/${userId}/role`, { new_role: newRole });
      await loadUsers();
    } catch {
    } finally {
      setChangingRole(null);
    }
  };

  const deactivate = async (userId: string) => {
    if (!confirm("Czy na pewno chcesz dezaktywować to konto?")) return;
    try {
      await api.post(`/api/v1/admin/users/${userId}/deactivate`);
      await loadUsers();
    } catch {}
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-400">Łącznie: <b className="text-white">{total}</b></span>
        <div className="flex gap-2">
          <select
            value={roleFilter}
            onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
            className="bg-white/5 border border-white/10 text-sm text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#d4af37]"
          >
            <option value="">Wszystkie role</option>
            <option value="admin">Admin</option>
            <option value="moderator">Moderator</option>
            <option value="user">User</option>
          </select>
          <button onClick={loadUsers} className="text-gray-500 hover:text-[#d4af37] transition-colors">
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500 animate-pulse">Ładuję...</div>
      ) : (
        <div className="space-y-2">
          {users.map((u) => (
            <div key={u.id} className={`bg-white/5 border ${u.is_active ? "border-white/10" : "border-red-900/30"} rounded-xl p-4`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm text-white truncate">{u.name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${ROLE_COLORS[u.role] || "bg-gray-800 text-gray-400"}`}>
                      {u.role}
                    </span>
                    {!u.is_active && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-red-900/40 text-red-400">
                        dezaktywowany
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">{u.email}</div>
                  <div className="text-xs text-gray-600 mt-0.5">{formatDate(u.created_at)}</div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <select
                    value={u.role}
                    onChange={(e) => changeRole(u.id, e.target.value)}
                    disabled={changingRole === u.id}
                    className="bg-white/5 border border-white/10 text-xs text-gray-300 rounded-lg px-2 py-1 focus:outline-none focus:border-[#d4af37] disabled:opacity-50"
                  >
                    <option value="user">user</option>
                    <option value="moderator">moderator</option>
                    <option value="admin">admin</option>
                  </select>
                  {u.is_active && (
                    <button
                      onClick={() => deactivate(u.id)}
                      className="text-xs text-red-400 hover:text-red-300 transition-colors px-2 py-1 rounded border border-red-900/30 hover:border-red-700/40"
                    >
                      Dezaktywuj
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Paginacja */}
      {total > 30 && (
        <div className="flex justify-center gap-3 mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="text-sm text-gray-400 hover:text-white disabled:opacity-30 px-3 py-1 border border-white/10 rounded-lg"
          >
            ← Poprzednia
          </button>
          <span className="text-sm text-gray-500 py-1">Strona {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={users.length < 30}
            className="text-sm text-gray-400 hover:text-white disabled:opacity-30 px-3 py-1 border border-white/10 rounded-lg"
          >
            Następna →
          </button>
        </div>
      )}
    </div>
  );
}

// ── Panel intencji ────────────────────────────────────────────────────────────

function IntentionsPanel() {
  const [intentions, setIntentions] = useState<Intention[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [moderating, setModerating] = useState<string | null>(null);
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<{ intentions: Intention[]; count: number }>("/api/v1/admin/intentions/pending");
      setIntentions(data.intentions);
      setCount(data.count);
    } catch {
      setIntentions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [load]);

  const approve = async (id: string) => {
    setModerating(id);
    try {
      await api.post(`/api/v1/admin/intentions/${id}/approve`);
      await load();
    } catch {
    } finally {
      setModerating(null);
    }
  };

  const reject = async () => {
    if (!rejectId || !rejectReason.trim()) return;
    setModerating(rejectId);
    try {
      await api.post(`/api/v1/admin/intentions/${rejectId}/reject`, { reason: rejectReason.trim() });
      setRejectId(null);
      setRejectReason("");
      await load();
    } catch {
    } finally {
      setModerating(null);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-400">
          Oczekujące: <b className={count > 0 ? "text-amber-400" : "text-white"}>{count}</b>
        </span>
        <button onClick={load} className="text-gray-500 hover:text-[#d4af37] transition-colors">
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500 animate-pulse">Ładuję...</div>
      ) : intentions.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-600" />
          <p>Brak intencji oczekujących na moderację.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {intentions.map((i) => (
            <div key={i.id} className="bg-white/5 border border-amber-700/20 rounded-xl p-4">
              <p className="text-sm text-gray-200 leading-relaxed mb-3">{i.content}</p>
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs text-gray-600">{formatDate(i.created_at)}</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => { setRejectId(i.id); setRejectReason(""); }}
                    disabled={moderating === i.id}
                    className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 px-3 py-1.5 border border-red-900/30 hover:border-red-700/40 rounded-lg transition-all disabled:opacity-50"
                  >
                    <XCircle className="h-3 w-3" /> Odrzuć
                  </button>
                  <button
                    onClick={() => approve(i.id)}
                    disabled={moderating === i.id}
                    className="flex items-center gap-1 text-xs text-green-400 hover:text-green-300 px-3 py-1.5 border border-green-900/30 hover:border-green-700/40 rounded-lg transition-all disabled:opacity-50"
                  >
                    <CheckCircle className="h-3 w-3" /> Zatwierdź
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal odrzucenia */}
      {rejectId && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4">
          <div className="bg-[#141028] border border-white/10 rounded-2xl p-6 w-full max-w-md">
            <h3 className="font-semibold text-white mb-3">Powód odrzucenia</h3>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={3}
              placeholder="Np. Treść narusza zasady moderacji..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-red-700/50 resize-none mb-4"
            />
            <div className="flex gap-3">
              <button
                onClick={() => setRejectId(null)}
                className="flex-1 py-2.5 text-sm text-gray-400 border border-white/10 rounded-xl hover:border-white/20 transition-all"
              >
                Anuluj
              </button>
              <button
                onClick={reject}
                disabled={!rejectReason.trim() || moderating !== null}
                className="flex-1 py-2.5 text-sm text-red-300 border border-red-900/40 rounded-xl hover:border-red-700/50 transition-all disabled:opacity-50"
              >
                Odrzuć intencję
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Panel AI Safety ───────────────────────────────────────────────────────────

function SafetyPanel() {
  const [interactions, setInteractions] = useState<AiInteraction[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filterModified, setFilterModified] = useState<boolean | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = { page: "1", page_size: "100" };
      if (filterModified !== null) params.was_modified = String(filterModified);
      const data = await api.get<{ interactions: AiInteraction[]; total: number }>(
        "/api/v1/admin/ai-interactions",
        { params }
      );
      setInteractions(data.interactions);
      setTotal(data.total);
    } catch {
      setInteractions([]);
    } finally {
      setLoading(false);
    }
  }, [filterModified]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [load]);

  const modified = interactions.filter((i) => i.was_modified).length;

  return (
    <div>
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-center">
          <div className="text-2xl font-bold text-white">{total}</div>
          <div className="text-xs text-gray-500 mt-0.5">Łączne interakcje</div>
        </div>
        <div className="bg-orange-900/20 border border-orange-700/30 rounded-xl p-3 text-center">
          <div className="text-2xl font-bold text-orange-300">{modified}</div>
          <div className="text-xs text-gray-500 mt-0.5">Zmodyfikowane przez AI</div>
        </div>
        <div className="bg-green-900/20 border border-green-700/30 rounded-xl p-3 text-center">
          <div className="text-2xl font-bold text-green-300">{total - modified}</div>
          <div className="text-xs text-gray-500 mt-0.5">Bezpieczne</div>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <span className="text-sm text-gray-500">Filtr:</span>
        {[null, true, false].map((val) => (
          <button
            key={String(val)}
            onClick={() => setFilterModified(val)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
              filterModified === val
                ? "border-[#d4af37] text-[#d4af37] bg-[#d4af37]/10"
                : "border-white/10 text-gray-400 hover:border-white/20"
            }`}
          >
            {val === null ? "Wszystkie" : val ? "Zmodyfikowane" : "Bezpieczne"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500 animate-pulse">Ładuję...</div>
      ) : (
        <div className="space-y-2">
          {interactions.map((i) => (
            <div
              key={i.id}
              className={`border rounded-xl p-3 ${
                i.was_modified
                  ? "bg-orange-900/10 border-orange-700/20"
                  : "bg-white/5 border-white/10"
              }`}
            >
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${RISK_COLORS[i.risk_category] || "bg-gray-800 text-gray-400"}`}>
                    {i.risk_category}
                  </span>
                  <span className="text-xs text-gray-400">{i.module}</span>
                  {i.was_modified && (
                    <span className="text-xs text-orange-400">⚠ zmodyfikowane</span>
                  )}
                </div>
                <span className="text-xs text-gray-600">{formatDate(i.created_at)}</span>
              </div>
              {i.violations && (
                <div className="text-xs text-orange-300/80 mt-1.5 pl-1 border-l border-orange-700/40">
                  {i.violations}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Panel logów audytu ────────────────────────────────────────────────────────

function LogsPanel() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<{ logs: AuditLog[]; total: number }>(
        "/api/v1/admin/audit-logs",
        { params: { page: String(page), page_size: "100" } }
      );
      setLogs(data.logs);
      setTotal(data.total);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [page]);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load(); }, [load]);

  const EVENT_COLOR: Record<string, string> = {
    USER_DELETED: "text-red-400",
    USER_ROLE_CHANGED: "text-orange-400",
    INTENTION_MODERATED: "text-blue-400",
    JOURNAL_ENTRY_DELETED: "text-violet-400",
    CONTENT_CREATED: "text-green-400",
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-400">Łącznie: <b className="text-white">{total}</b></span>
        <button onClick={load} className="text-gray-500 hover:text-[#d4af37] transition-colors">
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500 animate-pulse">Ładuję...</div>
      ) : (
        <div className="space-y-2">
          {logs.map((log) => (
            <div key={log.id} className="bg-white/5 border border-white/10 rounded-xl p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className={`text-xs font-mono font-medium ${EVENT_COLOR[log.event_type] || "text-gray-400"}`}>
                    {log.event_type}
                  </span>
                  <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">{log.description}</p>
                </div>
                <span className="text-xs text-gray-600 shrink-0">{formatDate(log.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {total > 100 && (
        <div className="flex justify-center gap-3 mt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="text-sm text-gray-400 hover:text-white disabled:opacity-30 px-3 py-1 border border-white/10 rounded-lg"
          >
            ← Poprzednia
          </button>
          <span className="text-sm text-gray-500 py-1">Strona {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={logs.length < 100}
            className="text-sm text-gray-400 hover:text-white disabled:opacity-30 px-3 py-1 border border-white/10 rounded-lg"
          >
            Następna →
          </button>
        </div>
      )}
    </div>
  );
}

// ── Strona główna admin ───────────────────────────────────────────────────────

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<Tab>("intentions");
  const [accessError, setAccessError] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    // Weryfikacja dostępu admina przez próbę API call
    api.get("/api/v1/admin/feature-flags")
      .then(() => setChecking(false))
      .catch((e) => {
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
          setAccessError(true);
        }
        setChecking(false);
      });
  }, []);

  if (checking) {
    return (
      <main className="min-h-screen bg-[#0d0b1a] flex items-center justify-center">
        <div className="text-gray-500 animate-pulse">Sprawdzam uprawnienia...</div>
      </main>
    );
  }

  if (accessError) {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white flex items-center justify-center px-4">
        <div className="text-center max-w-sm">
          <ShieldAlert className="h-16 w-16 text-red-600 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-red-400 mb-2">Brak dostępu</h1>
          <p className="text-gray-500 text-sm mb-6">
            Ta strona jest dostępna wyłącznie dla administratorów Sancta Nexus.
          </p>
          <a href="/" className="text-[#d4af37] text-sm underline">← Wróć do strony głównej</a>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white pb-24">
      {/* Nagłówek */}
      <div className="border-b border-white/10 bg-[#0d0b1a]/95 backdrop-blur sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <ShieldAlert className="h-5 w-5 text-[#d4af37]" />
            <h1 className="text-lg font-bold text-[#d4af37]">Panel Administracyjny</h1>
            <span className="text-xs text-gray-600 ml-auto">Sancta Nexus</span>
          </div>

          {/* Taby */}
          <div className="flex gap-1 mt-4 overflow-x-auto">
            {TAB_CONFIG.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap ${
                  activeTab === id
                    ? "bg-[#d4af37]/15 text-[#d4af37] border border-[#d4af37]/30"
                    : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Zawartość */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        {activeTab === "users" && <UsersPanel />}
        {activeTab === "intentions" && <IntentionsPanel />}
        {activeTab === "safety" && <SafetyPanel />}
        {activeTab === "logs" && <LogsPanel />}
      </div>
    </main>
  );
}
