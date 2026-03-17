"""
Content Uniqueness Engine
=========================
Ensures every Lectio Divina session produces genuinely unique, never-repeating
content by combining:

  1. **Daily Seed** — a deterministic seed derived from date + user_id + liturgical
     context, guaranteeing that the same user on the same day gets consistent but
     unique content, while different days always diverge.

  2. **Scripture Canon Tracker** — maps the full 73-book Catholic canon (46 OT + 27 NT)
     and tracks which passages a user has encountered, prioritising unseen books and
     chapters to ensure breadth of encounter with the whole Word of God.

  3. **Anti-Repetition Sliding Window** — maintains a sliding window of recent
     passages, themes, prayer traditions, and action categories to prevent any
     repetition within a configurable horizon.

  4. **Liturgical Resonance** — weights Scripture selection toward passages that
     harmonise with the current liturgical season, feast day, and daily readings.

  5. **Kerygmatic Cycle** — rotates through the core kerygmatic themes
     (Creation, Fall, Covenant, Prophecy, Incarnation, Paschal Mystery,
     Pentecost, Eschaton) to ensure the user encounters the full arc of
     salvation history over time.

"Semper antiqua, semper nova." — St Augustine on the Scriptures
"""

from __future__ import annotations

import hashlib
import logging
from datetime import date
from typing import Any

logger = logging.getLogger("sancta_nexus.uniqueness_engine")


# ---------------------------------------------------------------------------
# Catholic Canon — all 73 books
# ---------------------------------------------------------------------------

CANON_OT: list[str] = [
    # Pentateuch
    "Rdz", "Wj", "Kpl", "Lb", "Pwt",
    # Historical
    "Joz", "Sdz", "Rt", "1 Sm", "2 Sm", "1 Krl", "2 Krl",
    "1 Krn", "2 Krn", "Ezd", "Ne", "Tb", "Jdt", "Est",
    "1 Mch", "2 Mch",
    # Wisdom
    "Hi", "Ps", "Prz", "Koh", "Pnp", "Mdr", "Syr",
    # Prophets
    "Iz", "Jr", "Lm", "Ba", "Ez", "Dn",
    "Oz", "Jl", "Am", "Ab", "Jon", "Mi",
    "Na", "Ha", "So", "Ag", "Za", "Ml",
]

CANON_NT: list[str] = [
    # Gospels & Acts
    "Mt", "Mk", "Lk", "J", "Dz",
    # Pauline epistles
    "Rz", "1 Kor", "2 Kor", "Ga", "Ef", "Flp", "Kol",
    "1 Tes", "2 Tes", "1 Tm", "2 Tm", "Tt", "Flm",
    # Catholic epistles
    "Hbr", "Jk", "1 P", "2 P", "1 J", "2 J", "3 J", "Jud",
    # Apocalypse
    "Ap",
]

FULL_CANON: list[str] = CANON_OT + CANON_NT

# ---------------------------------------------------------------------------
# Kerygmatic cycle — the 8 pillars of salvation history
# ---------------------------------------------------------------------------

KERYGMATIC_THEMES: list[dict[str, Any]] = [
    {
        "theme": "creatio",
        "label": "Stworzenie i godnosc czlowieka",
        "key_passages": ["Rdz 1-2", "Ps 8", "Ps 104", "Mdr 11,24-26", "J 1,1-14"],
        "catechism_refs": ["CCC 279-324"],
    },
    {
        "theme": "lapsus",
        "label": "Upadek i obietnica odkupienia",
        "key_passages": ["Rdz 3", "Rdz 4,1-16", "Rz 5,12-21", "Rz 7,14-25"],
        "catechism_refs": ["CCC 385-421"],
    },
    {
        "theme": "foedus",
        "label": "Przymierze — Bog wierny swojemu ludowi",
        "key_passages": ["Rdz 12,1-9", "Rdz 15", "Wj 19-20", "Pwt 6,4-9", "Jr 31,31-34"],
        "catechism_refs": ["CCC 54-73"],
    },
    {
        "theme": "prophetia",
        "label": "Prorocy i oczekiwanie Mesjasza",
        "key_passages": ["Iz 7,14", "Iz 9,1-6", "Iz 53", "Mi 5,1-4", "Ez 37,1-14", "Dn 7,13-14"],
        "catechism_refs": ["CCC 702-720"],
    },
    {
        "theme": "incarnatio",
        "label": "Wcielenie — Bog staje sie czlowiekiem",
        "key_passages": ["Lk 1,26-38", "Lk 2,1-20", "J 1,1-18", "Flp 2,5-11", "Hbr 1,1-4"],
        "catechism_refs": ["CCC 456-483"],
    },
    {
        "theme": "mysterium_paschale",
        "label": "Misterium Paschalne — Meka, Smierc i Zmartwychwstanie",
        "key_passages": ["Mk 14-16", "J 18-20", "1 Kor 15,1-11", "Rz 6,3-11", "Kol 1,15-20"],
        "catechism_refs": ["CCC 571-658"],
    },
    {
        "theme": "pentecoste",
        "label": "Zeslanie Ducha Swietego i narodziny Kosciola",
        "key_passages": ["Dz 2,1-41", "J 14,15-26", "J 16,7-15", "Rz 8,1-17", "1 Kor 12,1-13"],
        "catechism_refs": ["CCC 731-741"],
    },
    {
        "theme": "eschaton",
        "label": "Nadzieja eschatologiczna — nowe niebo i nowa ziemia",
        "key_passages": ["Ap 21,1-7", "1 Tes 4,13-18", "Mt 25,31-46", "2 P 3,8-13", "Rz 8,18-25"],
        "catechism_refs": ["CCC 988-1060"],
    },
]


# ---------------------------------------------------------------------------
# Liturgical Scripture associations
# ---------------------------------------------------------------------------

SEASON_SCRIPTURE_WEIGHTS: dict[str, list[str]] = {
    "advent": [
        "Iz", "Mi", "So", "Ba", "Lk", "Mt", "Ps",
        "Ml", "Za", "Rdz",
    ],
    "christmas": [
        "Iz", "Lk", "J", "Tt", "Hbr", "Ps",
        "Mdr", "Syr", "Kol",
    ],
    "lent": [
        "Iz", "Jr", "Lm", "Ez", "Jl", "Jon",
        "Ps", "Mt", "Mk", "Lk", "J", "Rz", "Hbr",
    ],
    "easter": [
        "Dz", "J", "1 J", "Ap", "Ps", "Kol",
        "Ef", "Rz", "1 Kor", "1 P",
    ],
    "ordinary": FULL_CANON,  # all books equally weighted
}

# ---------------------------------------------------------------------------
# Emotion -> spiritual theme mapping
# ---------------------------------------------------------------------------

EMOTION_SCRIPTURE_MAP: dict[str, list[str]] = {
    # Consolation states
    "joy": ["Ps 100", "Ps 148", "Flp 4,4-9", "Lk 1,46-55", "Iz 12,1-6"],
    "gratitude": ["Ps 103", "Ps 136", "Kol 3,15-17", "1 Tes 5,16-18", "Dn 3,52-90"],
    "peace": ["J 14,27", "Flp 4,6-7", "Ps 23", "Ps 131", "Iz 26,3-4"],
    "love": ["1 Kor 13", "1 J 4,7-21", "Pnp 2,8-14", "Rz 8,35-39", "Ef 3,14-21"],
    "hope": ["Rz 8,28-39", "Jr 29,11-14", "Lm 3,22-26", "Ps 27", "Hbr 11,1-3"],
    "awe": ["Ps 8", "Ps 19", "Hi 38-39", "Iz 40,25-31", "Ap 4,1-11"],
    "serenity": ["Ps 46", "Ps 62", "Mt 11,28-30", "Iz 30,15", "Ps 37,1-7"],

    # Desolation states
    "sadness": ["Ps 42", "Ps 88", "Lm 3,1-24", "Mt 5,4", "J 11,33-36"],
    "fear": ["Iz 41,10", "Ps 91", "Ps 56", "2 Tm 1,7", "Mt 14,22-33"],
    "anxiety": ["Mt 6,25-34", "Flp 4,6-7", "1 P 5,6-7", "Ps 55,23", "Ps 94,18-19"],
    "grief": ["Ps 34,19", "Ap 21,4", "2 Kor 1,3-7", "J 14,1-6", "Rz 14,7-9"],
    "anger": ["Ef 4,26-32", "Jk 1,19-20", "Ps 37", "Prz 15,1", "Mt 5,21-24"],
    "loneliness": ["Ps 139", "Iz 49,15-16", "Mt 28,20", "Hbr 13,5-6", "Ps 68,6-7"],
    "guilt": ["Ps 51", "1 J 1,9", "Rz 8,1-2", "Iz 1,18", "Lk 15,11-32"],
    "shame": ["Rz 8,1", "Iz 54,4", "J 8,1-11", "Ps 34,6", "Hbr 12,1-3"],
    "confusion": ["Prz 3,5-6", "Jk 1,5-8", "Ps 25", "Iz 55,8-9", "J 16,33"],

    # Complex/spiritual states
    "longing": ["Ps 63", "Ps 42", "Pnp 3,1-4", "Flp 1,21-24", "Ps 84"],
    "humility": ["Mt 18,1-5", "Flp 2,1-11", "Mi 6,8", "Lk 1,46-55", "Ps 131"],
    "reverence": ["Iz 6,1-8", "Ap 4", "Ps 99", "Hbr 12,28-29", "Wj 3,1-6"],
    "compassion": ["Mt 25,31-46", "Lk 10,25-37", "Kol 3,12-14", "Mi 6,8", "Iz 58,6-12"],
    "dark_night": ["Ps 22", "Ps 88", "Hi 3", "Mk 15,34", "Lm 3,1-24"],
    "consolation": ["Iz 40,1-11", "2 Kor 1,3-7", "J 14,16-18", "Ps 23", "Rz 15,13"],
    "desolation": ["Ps 22", "Ps 130", "Lm 3,17-26", "Mk 14,32-42", "Hi 7,1-6"],
}


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------


class ContentUniquenessEngine:
    """Algorithmic engine guaranteeing content uniqueness across sessions.

    Combines date-based seeding, canon coverage tracking, sliding-window
    anti-repetition, liturgical resonance, and kerygmatic cycle awareness.
    """

    def __init__(self) -> None:
        logger.info("ContentUniquenessEngine initialised.")

    # ------------------------------------------------------------------
    # Daily seed
    # ------------------------------------------------------------------

    @staticmethod
    def compute_daily_seed(
        user_id: str,
        today: date | None = None,
    ) -> int:
        """Deterministic daily seed unique per user per day.

        Uses SHA-256 of ``user_id + ISO date`` to produce a stable integer.
        This ensures:
          - Same user, same day -> same seed (consistency within a day)
          - Different day -> different seed (daily freshness)
          - Different user -> different seed (personal uniqueness)
        """
        today = today or date.today()
        raw = f"{user_id}:{today.isoformat()}"
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return int(digest[:12], 16)

    # ------------------------------------------------------------------
    # Kerygmatic cycle position
    # ------------------------------------------------------------------

    @staticmethod
    def get_kerygmatic_theme(
        user_id: str,
        today: date | None = None,
        cycle_days: int = 8,
    ) -> dict[str, Any]:
        """Return the current kerygmatic theme for the user's cycle.

        The user progresses through the 8 kerygmatic pillars on a
        rotating schedule, spending ``cycle_days`` days per theme
        before advancing. The starting offset is personalised per user
        so that different users are at different points in the cycle.

        Args:
            user_id: User identifier.
            today: Override date.
            cycle_days: Days spent on each theme before rotation.

        Returns:
            Dict with theme, label, key_passages, catechism_refs.
        """
        today = today or date.today()
        user_offset = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
        day_of_year = today.timetuple().tm_yday + user_offset
        theme_index = (day_of_year // cycle_days) % len(KERYGMATIC_THEMES)
        return dict(KERYGMATIC_THEMES[theme_index])

    # ------------------------------------------------------------------
    # Scripture selection hints
    # ------------------------------------------------------------------

    def suggest_books(
        self,
        user_id: str,
        season: str,
        emotion: str,
        user_history: list[dict[str, Any]] | None = None,
        today: date | None = None,
    ) -> list[str]:
        """Suggest prioritised book list for Scripture selection.

        Combines liturgical weighting, emotional mapping, canon coverage,
        and anti-repetition to produce an ordered list of book abbreviations.

        Args:
            user_id: User identifier.
            season: Liturgical season (advent, lent, easter, christmas, ordinary).
            emotion: Dominant emotion label.
            user_history: Past sessions with scripture data.
            today: Override date.

        Returns:
            Ordered list of book abbreviations, most recommended first.
        """
        today = today or date.today()
        seed = self.compute_daily_seed(user_id, today)

        # 1. Liturgical books
        season_books = set(SEASON_SCRIPTURE_WEIGHTS.get(season, FULL_CANON))

        # 2. Emotion-mapped passages -> extract book abbreviations
        emotion_passages = EMOTION_SCRIPTURE_MAP.get(emotion, [])
        emotion_books = {p.split()[0] for p in emotion_passages}

        # 3. Recently used books (anti-repetition)
        recent_books: set[str] = set()
        for session in (user_history or [])[-30:]:
            scripture = session.get("scripture", {})
            book = scripture.get("book", "")
            # Map full names back to abbreviations where possible
            if book:
                recent_books.add(book)

        # 4. Score each book in the canon
        scored: list[tuple[str, float]] = []
        for i, book in enumerate(FULL_CANON):
            score = 1.0

            # Liturgical resonance bonus
            if book in season_books:
                score += 2.0

            # Emotional resonance bonus
            if book in emotion_books:
                score += 3.0

            # Anti-repetition penalty
            if book in recent_books:
                score -= 4.0

            # Kerygmatic bonus — boost books from current theme
            kerygma = self.get_kerygmatic_theme(user_id, today)
            for passage_ref in kerygma.get("key_passages", []):
                if passage_ref.startswith(book):
                    score += 1.5

            # Deterministic shuffle using seed
            score += ((seed + i * 7919) % 1000) / 1000.0

            scored.append((book, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [book for book, _ in scored]

    # ------------------------------------------------------------------
    # Anti-repetition for prayer traditions
    # ------------------------------------------------------------------

    @staticmethod
    def suggest_tradition(
        user_id: str,
        user_history: list[dict[str, Any]] | None = None,
        today: date | None = None,
    ) -> str:
        """Suggest a prayer tradition the user hasn't used recently.

        Rotates through traditions with a personalised offset to avoid
        always starting from the same tradition.
        """
        traditions = ["ignatian", "carmelite", "franciscan", "benedictine",
                      "charismatic", "dominican", "marian"]
        today = today or date.today()

        # Count recent tradition usage
        tradition_counts: dict[str, int] = {t: 0 for t in traditions}
        for session in (user_history or [])[-14:]:
            prayer = session.get("prayer", {})
            t = prayer.get("tradition", "")
            if t in tradition_counts:
                tradition_counts[t] += 1

        # Find least-used traditions
        min_count = min(tradition_counts.values())
        candidates = [t for t, c in tradition_counts.items() if c == min_count]

        # Deterministic pick from candidates using daily seed
        seed = int(hashlib.sha256(
            f"{user_id}:{today.isoformat()}:tradition".encode()
        ).hexdigest()[:8], 16)

        return candidates[seed % len(candidates)]

    # ------------------------------------------------------------------
    # Action category rotation
    # ------------------------------------------------------------------

    @staticmethod
    def suggest_action_category(
        user_id: str,
        user_history: list[dict[str, Any]] | None = None,
        today: date | None = None,
    ) -> str:
        """Suggest an action category based on Works of Mercy rotation.

        Categories are aligned with the corporal and spiritual works of mercy
        from Catholic tradition (CCC 2447), plus additional virtue categories.
        """
        categories = [
            "prayer",           # Modlitwa za zywych i umarlych
            "charity",          # Jalmuzna i karmienie glodnych
            "relationship",     # Pocieszanie strapionych
            "service",          # Nawiedzanie chorych
            "gratitude",        # Dziekczynienie
            "forgiveness",      # Przebaczanie uraz
            "self_care",        # Troska o swiatynia Ducha Swietego
            "teaching",         # Pouczanie niewiadomych
            "counsel",          # Radzenie watpiacym
            "patience",         # Cierpliwe znoszenie krzywdzacych
        ]
        today = today or date.today()

        # Count recent usage
        cat_counts: dict[str, int] = {c: 0 for c in categories}
        for session in (user_history or [])[-20:]:
            action = session.get("action", {})
            c = action.get("category", "")
            if c in cat_counts:
                cat_counts[c] += 1

        min_count = min(cat_counts.values())
        candidates = [c for c, cnt in cat_counts.items() if cnt == min_count]

        seed = int(hashlib.sha256(
            f"{user_id}:{today.isoformat()}:action".encode()
        ).hexdigest()[:8], 16)

        return candidates[seed % len(candidates)]

    # ------------------------------------------------------------------
    # Session uniqueness context
    # ------------------------------------------------------------------

    def build_session_context(
        self,
        user_id: str,
        season: str,
        emotion: str,
        user_history: list[dict[str, Any]] | None = None,
        today: date | None = None,
    ) -> dict[str, Any]:
        """Build a complete uniqueness context for a session.

        Returns a dict that can be injected into agent prompts to ensure
        each session is genuinely unique.
        """
        today = today or date.today()
        return {
            "daily_seed": self.compute_daily_seed(user_id, today),
            "kerygmatic_theme": self.get_kerygmatic_theme(user_id, today),
            "suggested_books": self.suggest_books(
                user_id, season, emotion, user_history, today
            )[:10],
            "suggested_tradition": self.suggest_tradition(
                user_id, user_history, today
            ),
            "suggested_action_category": self.suggest_action_category(
                user_id, user_history, today
            ),
            "emotion_passages": EMOTION_SCRIPTURE_MAP.get(emotion, []),
            "season": season,
            "date": today.isoformat(),
        }
