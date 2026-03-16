"""Neo4j-backed spiritual memory graph.

Stores and queries the user's spiritual journey as a knowledge graph,
tracking emotional states, scripture encounters, prayers, life events,
and the relationships between them.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Node & relation types
# ---------------------------------------------------------------------------


class NodeType(str, Enum):
    EMOTIONAL_STATE = "EmotionalState"
    SPIRITUAL_STATE = "SpiritualState"
    SCRIPTURE_ENCOUNTER = "ScriptureEncounter"
    PRAYER = "Prayer"
    LIFE_EVENT = "LifeEvent"
    GRACE_NOTE = "GraceNote"
    DARK_NIGHT = "DarkNight"
    DECISION = "Decision"
    THEME = "Theme"
    VIRTUE = "Virtue"


class RelationType(str, Enum):
    TRIGGERED_BY = "TRIGGERED_BY"
    LED_TO = "LED_TO"
    RESOLVED_BY = "RESOLVED_BY"
    ECHOES = "ECHOES"
    DEEPENED_BY = "DEEPENED_BY"
    CHALLENGED_BY = "CHALLENGED_BY"
    ANSWERED_THROUGH = "ANSWERED_THROUGH"
    CONNECTED_TO = "CONNECTED_TO"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SessionData:
    """Data captured during a single spiritual direction session."""

    session_id: str
    timestamp: datetime
    emotional_state: dict[str, float]
    spiritual_state: str
    scriptures_presented: list[str] = field(default_factory=list)
    user_reflection: str = ""
    prayer_type: str = ""
    life_events: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    grace_notes: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)


@dataclass
class Pattern:
    """A recurring pattern detected in the spiritual journey."""

    pattern_type: str
    description: str
    frequency: int
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    related_scriptures: list[str] = field(default_factory=list)
    strength: float = 0.0


@dataclass
class Theme:
    """A spiritual theme identified across sessions."""

    name: str
    occurrences: int
    related_emotions: list[str] = field(default_factory=list)
    related_scriptures: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class JourneyGraph:
    """Serialisable snapshot of a user's spiritual journey graph."""

    user_id: str
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# SpiritualMemoryGraph
# ---------------------------------------------------------------------------


class SpiritualMemoryGraph:
    """Neo4j-based spiritual memory graph.

    Persists the user's spiritual journey as a property graph with
    typed nodes (emotional states, scripture encounters, prayers,
    life events, etc.) and typed relationships.
    """

    def __init__(
        self,
        neo4j_uri: str | None = None,
        neo4j_user: str | None = None,
        neo4j_password: str | None = None,
    ) -> None:
        self._uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = neo4j_user or os.getenv("NEO4J_USER", "neo4j")
        self._password = neo4j_password or os.getenv("NEO4J_PASSWORD", "")
        self._driver = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _get_driver(self):
        """Lazily initialise the Neo4j driver."""
        if self._driver is None:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
            )
        return self._driver

    def close(self) -> None:
        """Close the Neo4j driver."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def _run_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict]:
        """Execute a Cypher query and return results as a list of dicts."""
        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    # ------------------------------------------------------------------
    # Schema initialisation
    # ------------------------------------------------------------------

    def ensure_schema(self) -> None:
        """Create indexes and constraints for the graph schema."""
        constraints = [
            (
                "CREATE CONSTRAINT IF NOT EXISTS "
                "FOR (u:User) REQUIRE u.user_id IS UNIQUE"
            ),
            (
                "CREATE CONSTRAINT IF NOT EXISTS "
                "FOR (s:Session) REQUIRE s.session_id IS UNIQUE"
            ),
        ]
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (e:EmotionalState) ON (e.timestamp)",
            "CREATE INDEX IF NOT EXISTS FOR (s:ScriptureEncounter) ON (s.reference)",
            "CREATE INDEX IF NOT EXISTS FOR (t:Theme) ON (t.name)",
        ]
        for stmt in constraints + indexes:
            self._run_query(stmt)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_session(self, user_id: str, session_data: SessionData) -> None:
        """Record a complete spiritual direction session in the graph.

        Creates nodes for the session's emotional state, spiritual state,
        any scripture encounters, prayers, life events, grace notes and
        themes -- and connects them via typed relationships.
        """
        # Ensure User node
        self._run_query(
            "MERGE (u:User {user_id: $uid})",
            {"uid": user_id},
        )

        # Session node
        self._run_query(
            """
            MERGE (s:Session {session_id: $sid})
            SET s.timestamp = datetime($ts),
                s.spiritual_state = $state
            WITH s
            MATCH (u:User {user_id: $uid})
            MERGE (u)-[:HAD_SESSION]->(s)
            """,
            {
                "sid": session_data.session_id,
                "ts": session_data.timestamp.isoformat(),
                "state": session_data.spiritual_state,
                "uid": user_id,
            },
        )

        # Emotional state node
        primary_emotion = max(session_data.emotional_state, key=session_data.emotional_state.get)
        self._run_query(
            """
            MATCH (s:Session {session_id: $sid})
            CREATE (e:EmotionalState {
                primary: $primary,
                vector: $vector,
                timestamp: datetime($ts)
            })
            CREATE (s)-[:HAD_EMOTION]->(e)
            """,
            {
                "sid": session_data.session_id,
                "primary": primary_emotion,
                "vector": str(session_data.emotional_state),
                "ts": session_data.timestamp.isoformat(),
            },
        )

        # Spiritual state node
        self._run_query(
            """
            MATCH (s:Session {session_id: $sid})
            CREATE (sp:SpiritualState {state: $state, timestamp: datetime($ts)})
            CREATE (s)-[:HAD_SPIRITUAL_STATE]->(sp)
            """,
            {
                "sid": session_data.session_id,
                "state": session_data.spiritual_state,
                "ts": session_data.timestamp.isoformat(),
            },
        )

        # Scripture encounters
        for ref in session_data.scriptures_presented:
            self._run_query(
                """
                MATCH (s:Session {session_id: $sid})
                MERGE (sc:ScriptureEncounter {reference: $ref})
                CREATE (s)-[:ENCOUNTERED_SCRIPTURE]->(sc)
                """,
                {"sid": session_data.session_id, "ref": ref},
            )

        # Life events
        for event in session_data.life_events:
            self._run_query(
                """
                MATCH (s:Session {session_id: $sid})
                CREATE (le:LifeEvent {description: $desc, timestamp: datetime($ts)})
                CREATE (s)-[:INVOLVED_EVENT]->(le)
                """,
                {
                    "sid": session_data.session_id,
                    "desc": event,
                    "ts": session_data.timestamp.isoformat(),
                },
            )

        # Grace notes
        for note in session_data.grace_notes:
            self._run_query(
                """
                MATCH (s:Session {session_id: $sid})
                CREATE (gn:GraceNote {content: $content, timestamp: datetime($ts)})
                CREATE (s)-[:RECEIVED_GRACE]->(gn)
                """,
                {
                    "sid": session_data.session_id,
                    "content": note,
                    "ts": session_data.timestamp.isoformat(),
                },
            )

        # Themes
        for theme_name in session_data.themes:
            self._run_query(
                """
                MATCH (s:Session {session_id: $sid})
                MERGE (t:Theme {name: $name})
                ON CREATE SET t.occurrences = 1
                ON MATCH SET t.occurrences = t.occurrences + 1
                CREATE (s)-[:TOUCHED_THEME]->(t)
                """,
                {"sid": session_data.session_id, "name": theme_name},
            )

        # Decisions
        for decision in session_data.decisions:
            self._run_query(
                """
                MATCH (s:Session {session_id: $sid})
                CREATE (d:Decision {description: $desc, timestamp: datetime($ts)})
                CREATE (s)-[:MADE_DECISION]->(d)
                """,
                {
                    "sid": session_data.session_id,
                    "desc": decision,
                    "ts": session_data.timestamp.isoformat(),
                },
            )

        # Link emotional -> spiritual state
        self._run_query(
            """
            MATCH (s:Session {session_id: $sid})-[:HAD_EMOTION]->(e:EmotionalState)
            MATCH (s)-[:HAD_SPIRITUAL_STATE]->(sp:SpiritualState)
            CREATE (e)-[:LED_TO]->(sp)
            """,
            {"sid": session_data.session_id},
        )

        logger.info("Recorded session %s for user %s", session_data.session_id, user_id)

    def get_spiritual_journey(self, user_id: str) -> JourneyGraph:
        """Retrieve the full spiritual journey graph for a user.

        Returns a serialisable :class:`JourneyGraph` containing all
        nodes and edges.
        """
        nodes_result = self._run_query(
            """
            MATCH (u:User {user_id: $uid})-[:HAD_SESSION]->(s:Session)
            OPTIONAL MATCH (s)-[r]->(n)
            RETURN s, type(r) AS rel_type, labels(n) AS node_labels,
                   properties(n) AS node_props, id(n) AS node_id
            ORDER BY s.timestamp
            """,
            {"uid": user_id},
        )

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        seen_ids: set[int] = set()

        for row in nodes_result:
            node_id = row.get("node_id")
            if node_id and node_id not in seen_ids:
                seen_ids.add(node_id)
                nodes.append({
                    "id": node_id,
                    "labels": row.get("node_labels", []),
                    "properties": row.get("node_props", {}),
                })
            if row.get("rel_type"):
                edges.append({
                    "type": row["rel_type"],
                    "target_id": node_id,
                })

        return JourneyGraph(user_id=user_id, nodes=nodes, edges=edges)

    def find_patterns(self, user_id: str) -> list[Pattern]:
        """Detect recurring patterns in the user's spiritual journey.

        Looks for repeated emotion sequences, recurring scripture-emotion
        pairings, and cyclical spiritual states.
        """
        # Recurring emotional patterns
        emotion_patterns = self._run_query(
            """
            MATCH (u:User {user_id: $uid})-[:HAD_SESSION]->(s:Session)
                  -[:HAD_EMOTION]->(e:EmotionalState)
            WITH e.primary AS emotion, count(*) AS cnt,
                 min(e.timestamp) AS first, max(e.timestamp) AS last
            WHERE cnt >= 2
            RETURN emotion, cnt, first, last
            ORDER BY cnt DESC
            """,
            {"uid": user_id},
        )

        # Scripture-emotion pairings
        scripture_patterns = self._run_query(
            """
            MATCH (u:User {user_id: $uid})-[:HAD_SESSION]->(s:Session)
                  -[:ENCOUNTERED_SCRIPTURE]->(sc:ScriptureEncounter)
            MATCH (s)-[:HAD_EMOTION]->(e:EmotionalState)
            WITH sc.reference AS ref, e.primary AS emotion, count(*) AS cnt
            WHERE cnt >= 2
            RETURN ref, emotion, cnt
            ORDER BY cnt DESC
            """,
            {"uid": user_id},
        )

        patterns: list[Pattern] = []

        for row in emotion_patterns:
            patterns.append(Pattern(
                pattern_type="recurring_emotion",
                description=f"Recurring emotion: {row['emotion']}",
                frequency=row["cnt"],
                first_seen=row.get("first"),
                last_seen=row.get("last"),
                strength=min(1.0, row["cnt"] / 10),
            ))

        for row in scripture_patterns:
            patterns.append(Pattern(
                pattern_type="scripture_emotion_pairing",
                description=(
                    f"Scripture {row['ref']} frequently paired with "
                    f"emotion '{row['emotion']}'"
                ),
                frequency=row["cnt"],
                related_scriptures=[row["ref"]],
                strength=min(1.0, row["cnt"] / 5),
            ))

        return patterns

    def get_recurring_themes(self, user_id: str) -> list[Theme]:
        """Return themes that recur across the user's sessions."""
        results = self._run_query(
            """
            MATCH (u:User {user_id: $uid})-[:HAD_SESSION]->(s:Session)
                  -[:TOUCHED_THEME]->(t:Theme)
            OPTIONAL MATCH (s)-[:HAD_EMOTION]->(e:EmotionalState)
            OPTIONAL MATCH (s)-[:ENCOUNTERED_SCRIPTURE]->(sc:ScriptureEncounter)
            WITH t.name AS theme, t.occurrences AS occ,
                 collect(DISTINCT e.primary) AS emotions,
                 collect(DISTINCT sc.reference) AS scriptures
            RETURN theme, occ, emotions, scriptures
            ORDER BY occ DESC
            """,
            {"uid": user_id},
        )

        return [
            Theme(
                name=row["theme"],
                occurrences=row["occ"],
                related_emotions=[e for e in row.get("emotions", []) if e],
                related_scriptures=[s for s in row.get("scriptures", []) if s],
            )
            for row in results
        ]

    def spiritual_pagerank(self, user_id: str) -> dict[str, float]:
        """Run a PageRank-style analysis on the user's spiritual graph.

        Identifies the most influential nodes (scriptures, emotions,
        themes) in the user's journey.

        Returns:
            Mapping of ``"NodeType:identifier"`` to importance score.
        """
        results = self._run_query(
            """
            MATCH (u:User {user_id: $uid})-[:HAD_SESSION]->(s:Session)
            MATCH (s)-[r]->(n)
            WITH labels(n)[0] AS label, properties(n) AS props,
                 count(r) AS degree
            RETURN label,
                   CASE
                     WHEN label = 'Theme' THEN props.name
                     WHEN label = 'ScriptureEncounter' THEN props.reference
                     WHEN label = 'EmotionalState' THEN props.primary
                     ELSE coalesce(props.description, props.state, toString(id(n)))
                   END AS identifier,
                   degree
            ORDER BY degree DESC
            LIMIT 20
            """,
            {"uid": user_id},
        )

        if not results:
            return {}

        max_degree = max(row["degree"] for row in results)
        return {
            f"{row['label']}:{row['identifier']}": round(row["degree"] / max_degree, 4)
            for row in results
        }
