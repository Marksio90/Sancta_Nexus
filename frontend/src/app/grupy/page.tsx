"use client";

import { useState, useEffect, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const CATEGORY_META: Record<string, { icon: string; color: string }> = {
  rodziny: { icon: "👨‍👩‍👧", color: "from-rose-900/40 to-rose-800/20" },
  młodzież: { icon: "🌟", color: "from-yellow-900/40 to-yellow-800/20" },
  seniorzy: { icon: "🤍", color: "from-gray-700/40 to-gray-600/20" },
  chorzy: { icon: "❤", color: "from-red-900/40 to-red-800/20" },
  różaniec: { icon: "📿", color: "from-blue-900/40 to-blue-800/20" },
  adoracja: { icon: "✨", color: "from-amber-900/40 to-amber-800/20" },
  ewangelizacja: { icon: "🌍", color: "from-green-900/40 to-green-800/20" },
  lectio_divina: { icon: "📖", color: "from-purple-900/40 to-purple-800/20" },
  ogólna: { icon: "⛪", color: "from-slate-700/40 to-slate-600/20" },
};

const ALL_CATEGORIES = [
  "all",
  "różaniec",
  "adoracja",
  "rodziny",
  "młodzież",
  "lectio_divina",
  "seniorzy",
  "chorzy",
  "ewangelizacja",
  "ogólna",
];

type AppState = "list" | "detail" | "new";

export default function GrupyPage() {
  const [appState, setAppState] = useState<AppState>("list");
  const [groups, setGroups] = useState<any[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<any>(null);
  const [category, setCategory] = useState("all");
  const [loading, setLoading] = useState(true);
  const [joinedIds, setJoinedIds] = useState<Set<string>>(new Set());

  // New group form
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [newCategory, setNewCategory] = useState("ogólna");
  const [schedule, setSchedule] = useState("");
  const [parish, setParish] = useState("");
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState(false);

  const loadGroups = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API}/api/v1/community/groups?category=${category}`
      );
      const data = await res.json();
      setGroups(data.groups || []);
    } catch {
      setGroups([]);
    } finally {
      setLoading(false);
    }
  }, [category]);

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  const join = async (groupId: string) => {
    if (joinedIds.has(groupId)) return;
    // Simulate user_id — in production use real auth token
    const userId = "guest-" + Math.random().toString(36).slice(2, 8);
    try {
      const res = await fetch(
        `${API}/api/v1/community/groups/${groupId}/join?user_id=${userId}`,
        { method: "POST" }
      );
      const data = await res.json();
      if (data.joined !== false) {
        setJoinedIds((prev) => new Set([...prev, groupId]));
        setGroups((prev) =>
          prev.map((g) =>
            g.id === groupId ? { ...g, member_count: g.member_count + 1 } : g
          )
        );
      }
    } catch {}
  };

  const createGroup = async () => {
    if (!name.trim() || creating) return;
    setCreating(true);
    try {
      await fetch(`${API}/api/v1/community/groups`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          category: newCategory,
          schedule: schedule.trim() || null,
          parish: parish.trim() || null,
        }),
      });
      setCreated(true);
      setTimeout(() => {
        setCreated(false);
        setAppState("list");
        setName("");
        setDescription("");
        setSchedule("");
        setParish("");
        loadGroups();
      }, 2000);
    } catch {
      setCreating(false);
    }
  };

  // ── New group ──────────────────────────────────────────────────────────────
  if (appState === "new") {
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-lg mx-auto px-4 py-10 pb-24">
          <div className="flex items-center gap-3 mb-8">
            <button onClick={() => setAppState("list")} className="text-gray-400 hover:text-white">←</button>
            <h1 className="text-xl font-bold text-[#d4af37]">Nowa grupa modlitewna</h1>
          </div>

          {created ? (
            <div className="text-center py-16">
              <div className="text-5xl mb-4">👥</div>
              <p className="text-[#d4af37] font-semibold text-lg">Grupa utworzona!</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-300 mb-1">Nazwa grupy *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={200}
                  placeholder="np. Żywy Różaniec — Parafia Świętego Jana"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-[#d4af37]"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Opis</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  maxLength={500}
                  placeholder="Czym zajmuje się wasza grupa? Dla kogo jest przeznaczona?"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-[#d4af37] resize-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Kategoria</label>
                <div className="flex flex-wrap gap-2">
                  {ALL_CATEGORIES.filter((c) => c !== "all").map((c) => (
                    <button
                      key={c}
                      onClick={() => setNewCategory(c)}
                      className={`text-xs px-3 py-1.5 rounded-full border transition-all ${
                        newCategory === c
                          ? "bg-[#d4af37] border-[#d4af37] text-black font-semibold"
                          : "bg-white/5 border-white/10 text-gray-400"
                      }`}
                    >
                      {CATEGORY_META[c]?.icon || "⛪"} {c}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Harmonogram</label>
                <input
                  type="text"
                  value={schedule}
                  onChange={(e) => setSchedule(e.target.value)}
                  placeholder="np. Wtorki 19:00, Pierwszy piątek miesiąca"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-[#d4af37]"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-300 mb-1">Parafia / Miejsce</label>
                <input
                  type="text"
                  value={parish}
                  onChange={(e) => setParish(e.target.value)}
                  placeholder="np. Parafia Wniebowzięcia NMP, Warszawa"
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-[#d4af37]"
                />
              </div>
              <button
                onClick={createGroup}
                disabled={!name.trim() || creating}
                className="w-full bg-[#d4af37] text-black font-semibold py-4 rounded-2xl hover:bg-[#c9a227] transition-colors disabled:opacity-50"
              >
                {creating ? "Tworzę grupę..." : "Utwórz grupę 👥"}
              </button>
            </div>
          )}
        </div>
      </main>
    );
  }

  // ── Group detail ──────────────────────────────────────────────────────────
  if (appState === "detail" && selectedGroup) {
    const meta = CATEGORY_META[selectedGroup.category] || CATEGORY_META["ogólna"];
    const joined = joinedIds.has(selectedGroup.id);
    return (
      <main className="min-h-screen bg-[#0d0b1a] text-white">
        <div className="max-w-2xl mx-auto px-4 py-10 pb-24">
          <div className="flex items-center gap-3 mb-6">
            <button onClick={() => setAppState("list")} className="text-gray-400 hover:text-white">←</button>
            <h1 className="text-xl font-bold text-[#d4af37]">{selectedGroup.name}</h1>
          </div>

          <div className={`rounded-2xl bg-gradient-to-br ${meta.color} border border-white/10 p-6 mb-6`}>
            <div className="text-4xl mb-3">{meta.icon}</div>
            <p className="text-gray-200 leading-relaxed mb-4">{selectedGroup.description || "Brak opisu."}</p>
            <div className="space-y-1 text-sm text-gray-400">
              {selectedGroup.parish && <div>⛪ {selectedGroup.parish}</div>}
              {selectedGroup.schedule && <div>🕐 {selectedGroup.schedule}</div>}
              <div>👥 {selectedGroup.member_count} członków</div>
              <div className="text-xs text-gray-600">Kategoria: {selectedGroup.category}</div>
            </div>
          </div>

          <button
            onClick={() => join(selectedGroup.id)}
            disabled={joined}
            className={`w-full font-semibold py-4 rounded-2xl transition-colors ${
              joined
                ? "bg-emerald-700/50 border border-emerald-600/50 text-emerald-300 cursor-default"
                : "bg-[#d4af37] text-black hover:bg-[#c9a227]"
            }`}
          >
            {joined ? "✓ Dołączyłeś do grupy" : "Dołącz do grupy"}
          </button>
        </div>
      </main>
    );
  }

  // ── List ──────────────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white">
      <div className="max-w-2xl mx-auto px-4 py-10 pb-24">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-[#d4af37]">👥 Grupy modlitewne</h1>
            <p className="text-gray-500 text-xs mt-0.5">Parafia i online</p>
          </div>
          <button
            onClick={() => setAppState("new")}
            className="bg-emerald-700/60 hover:bg-emerald-700/80 text-white text-sm font-medium px-4 py-2 rounded-xl border border-emerald-600/50 transition-colors"
          >
            + Nowa
          </button>
        </div>

        {/* Category filter */}
        <div className="flex gap-2 overflow-x-auto pb-2 mb-6 scrollbar-hide">
          {ALL_CATEGORIES.map((c) => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={`whitespace-nowrap text-xs px-3 py-1.5 rounded-full border flex-shrink-0 transition-all ${
                category === c
                  ? "bg-[#d4af37] border-[#d4af37] text-black font-semibold"
                  : "bg-white/5 border-white/10 text-gray-400 hover:border-white/30"
              }`}
            >
              {c === "all" ? "Wszystkie" : `${CATEGORY_META[c]?.icon || "⛪"} ${c}`}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((n) => (
              <div key={n} className="bg-white/5 rounded-xl p-4 h-24 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {groups.map((group) => {
              const meta = CATEGORY_META[group.category] || CATEGORY_META["ogólna"];
              const joined = joinedIds.has(group.id);
              return (
                <button
                  key={group.id}
                  onClick={() => { setSelectedGroup(group); setAppState("detail"); }}
                  className="w-full bg-white/5 hover:bg-white/10 border border-white/10 hover:border-emerald-600/40 rounded-xl p-4 text-left transition-all"
                >
                  <div className="flex items-start gap-3">
                    <div className="text-2xl">{meta.icon}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <div className="font-medium text-sm text-white truncate">
                          {group.name}
                        </div>
                        {joined && (
                          <span className="text-xs text-emerald-400 ml-2 flex-shrink-0">
                            ✓ Dołączyłeś
                          </span>
                        )}
                      </div>
                      {group.description && (
                        <p className="text-xs text-gray-500 line-clamp-1 mb-1">
                          {group.description}
                        </p>
                      )}
                      <div className="flex gap-3 text-xs text-gray-600">
                        {group.schedule && <span>🕐 {group.schedule}</span>}
                        <span>👥 {group.member_count}</span>
                        {group.parish && <span>⛪ {group.parish}</span>}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
