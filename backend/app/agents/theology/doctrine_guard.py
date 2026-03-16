"""
DoctrineGuardAgent (A-021) - Final safety gate for doctrinal fidelity.

Binary classifier that blocks any content contradicting the
Nicene-Constantinopolitan Creed and 47 key Catholic dogmas.
This is a CRITICAL safety component: if any violation is detected
the content is rejected entirely.

Uses an LLM to check content against core dogmas and returns a dict
with ``passed`` (bool), ``violations`` (list), and ``confidence`` (float).
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


# The 47 key dogmas organised by theological category.
# Each dogma has an id, short label, and a description for the classifier.
DOGMAS: list[dict[str, str]] = [
    # --- Trinity ---
    {"id": "T-01", "category": "Trinity", "label": "One God",
     "desc": "There is only one God, who is eternal, infinite, and almighty."},
    {"id": "T-02", "category": "Trinity", "label": "Trinity of Persons",
     "desc": "In God there are three Persons: Father, Son, and Holy Spirit."},
    {"id": "T-03", "category": "Trinity", "label": "Consubstantiality",
     "desc": "The three Persons are consubstantial (homoousios), co-equal, and co-eternal."},
    {"id": "T-04", "category": "Trinity", "label": "Filioque",
     "desc": "The Holy Spirit proceeds from the Father and the Son."},
    {"id": "T-05", "category": "Trinity", "label": "Perichoresis",
     "desc": "The divine Persons mutually indwell one another."},

    # --- Incarnation / Christology ---
    {"id": "C-01", "category": "Incarnation", "label": "True God and True Man",
     "desc": "Jesus Christ is true God and true man, one Person in two natures."},
    {"id": "C-02", "category": "Incarnation", "label": "Hypostatic Union",
     "desc": "The divine and human natures are united in the one Person of the Word without confusion, change, division, or separation."},
    {"id": "C-03", "category": "Incarnation", "label": "Virgin Birth",
     "desc": "Jesus was conceived by the Holy Spirit and born of the Virgin Mary."},
    {"id": "C-04", "category": "Incarnation", "label": "Bodily Resurrection",
     "desc": "Jesus Christ truly rose from the dead in his body on the third day."},
    {"id": "C-05", "category": "Incarnation", "label": "Ascension",
     "desc": "Jesus Christ ascended bodily into heaven and sits at the right hand of the Father."},
    {"id": "C-06", "category": "Incarnation", "label": "Second Coming",
     "desc": "Christ will come again in glory to judge the living and the dead."},
    {"id": "C-07", "category": "Incarnation", "label": "Redemption through the Cross",
     "desc": "Christ redeemed humanity through his suffering and death on the Cross."},

    # --- Eucharist ---
    {"id": "E-01", "category": "Eucharist", "label": "Real Presence",
     "desc": "Christ is truly, really, and substantially present in the Eucharist."},
    {"id": "E-02", "category": "Eucharist", "label": "Transubstantiation",
     "desc": "The substance of bread and wine is changed into the Body and Blood of Christ."},
    {"id": "E-03", "category": "Eucharist", "label": "Eucharist as Sacrifice",
     "desc": "The Eucharist is the sacrifice of the Body and Blood of Christ, re-presenting Calvary."},

    # --- Mary ---
    {"id": "M-01", "category": "Mary", "label": "Theotokos",
     "desc": "Mary is the Mother of God (Theotokos)."},
    {"id": "M-02", "category": "Mary", "label": "Immaculate Conception",
     "desc": "Mary was conceived without original sin by a singular grace of God."},
    {"id": "M-03", "category": "Mary", "label": "Perpetual Virginity",
     "desc": "Mary remained a virgin before, during, and after the birth of Christ."},
    {"id": "M-04", "category": "Mary", "label": "Assumption",
     "desc": "Mary was assumed body and soul into heavenly glory at the end of her earthly life."},

    # --- Salvation and Grace ---
    {"id": "S-01", "category": "Salvation", "label": "Original Sin",
     "desc": "All humans inherit original sin from Adam and Eve."},
    {"id": "S-02", "category": "Salvation", "label": "Necessity of Grace",
     "desc": "Salvation is impossible without God's grace."},
    {"id": "S-03", "category": "Salvation", "label": "Faith and Works",
     "desc": "Both faith and works, empowered by grace, are necessary for salvation."},
    {"id": "S-04", "category": "Salvation", "label": "Baptismal Regeneration",
     "desc": "Baptism truly forgives sins and regenerates the soul."},
    {"id": "S-05", "category": "Salvation", "label": "Universal Salvific Will",
     "desc": "God sincerely wills the salvation of all people."},
    {"id": "S-06", "category": "Salvation", "label": "Particular Judgement",
     "desc": "Each soul undergoes particular judgement immediately after death."},
    {"id": "S-07", "category": "Salvation", "label": "Purgatory",
     "desc": "There exists a state of purification (Purgatory) after death for those who die in grace but are not yet fully purified."},
    {"id": "S-08", "category": "Salvation", "label": "Heaven and Hell",
     "desc": "Heaven and hell are real, eternal states; heaven is communion with God, hell is definitive self-exclusion from God."},

    # --- Grace ---
    {"id": "G-01", "category": "Grace", "label": "Sanctifying Grace",
     "desc": "Sanctifying grace is a habitual gift, a stable disposition to live and act in keeping with God's call."},
    {"id": "G-02", "category": "Grace", "label": "Freedom and Grace",
     "desc": "Grace does not destroy but perfects human freedom; humans can cooperate with or resist grace."},
    {"id": "G-03", "category": "Grace", "label": "Justification",
     "desc": "Justification is not merely forensic but involves true interior renewal by the Holy Spirit."},

    # --- Church and Sacraments ---
    {"id": "CH-01", "category": "Church", "label": "One Holy Catholic Apostolic Church",
     "desc": "The Church is one, holy, catholic, and apostolic."},
    {"id": "CH-02", "category": "Church", "label": "Petrine Primacy",
     "desc": "The Pope, as successor of Peter, holds primacy of jurisdiction over the whole Church."},
    {"id": "CH-03", "category": "Church", "label": "Papal Infallibility",
     "desc": "The Pope is infallible when he speaks ex cathedra on matters of faith and morals."},
    {"id": "CH-04", "category": "Church", "label": "Apostolic Succession",
     "desc": "Bishops are successors of the Apostles by divine institution."},
    {"id": "CH-05", "category": "Church", "label": "Seven Sacraments",
     "desc": "There are seven sacraments instituted by Christ: Baptism, Confirmation, Eucharist, Penance, Anointing of the Sick, Holy Orders, and Matrimony."},
    {"id": "CH-06", "category": "Church", "label": "Communion of Saints",
     "desc": "The faithful on earth, souls in Purgatory, and saints in heaven form one communion."},
    {"id": "CH-07", "category": "Church", "label": "Necessity of the Church",
     "desc": "The Church is necessary for salvation as the universal sacrament of salvation."},

    # --- Scripture and Revelation ---
    {"id": "R-01", "category": "Revelation", "label": "Divine Inspiration of Scripture",
     "desc": "Sacred Scripture is divinely inspired and teaches truth without error in matters of faith and morals."},
    {"id": "R-02", "category": "Revelation", "label": "Scripture and Tradition",
     "desc": "Sacred Scripture and Sacred Tradition together form the single deposit of the Word of God."},
    {"id": "R-03", "category": "Revelation", "label": "Magisterium",
     "desc": "The task of authentically interpreting the Word of God belongs to the living Magisterium of the Church."},
    {"id": "R-04", "category": "Revelation", "label": "Canon of Scripture",
     "desc": "The canon of Scripture includes 46 Old Testament and 27 New Testament books."},

    # --- Moral Theology ---
    {"id": "MT-01", "category": "Moral", "label": "Natural Law",
     "desc": "There exists a natural moral law inscribed in the human heart, accessible to reason."},
    {"id": "MT-02", "category": "Moral", "label": "Dignity of Human Life",
     "desc": "Human life is sacred from conception to natural death."},
    {"id": "MT-03", "category": "Moral", "label": "Free Will",
     "desc": "Humans possess genuine free will and moral responsibility."},

    # --- Eschatology ---
    {"id": "ES-01", "category": "Eschatology", "label": "General Resurrection",
     "desc": "All the dead will rise with their bodies on the last day."},
    {"id": "ES-02", "category": "Eschatology", "label": "Last Judgement",
     "desc": "There will be a general judgement of all humanity at the end of time."},
    {"id": "ES-03", "category": "Eschatology", "label": "New Creation",
     "desc": "God will bring about a new heaven and a new earth."},
]


class DoctrineGuardAgent:
    """
    A-021: Final safety gate - blocks content contradicting key Catholic dogmas.

    This is a CRITICAL safety component. Any content that contradicts even
    a single dogma of the Nicene-Constantinopolitan Creed or the 47 key
    dogmas is rejected entirely.

    Uses an LLM to evaluate content against all dogmas and returns a dict
    with ``passed``, ``violations``, and ``confidence``.
    """

    AGENT_ID = "A-021"
    AGENT_NAME = "DoctrineGuardAgent"

    _SYSTEM_PROMPT = (
        "You are a Catholic doctrinal classifier. Your ONLY task is to "
        "determine whether the given content CONTRADICTS any of the listed "
        "dogmas of the Catholic faith.\n\n"
        "IMPORTANT RULES:\n"
        "- You must check the content against EVERY dogma listed.\n"
        "- A contradiction means the content explicitly or implicitly DENIES "
        "or OPPOSES the dogma.\n"
        "- Silence on a dogma is NOT a contradiction.\n"
        "- Merely discussing a dogma or presenting it for educational purposes "
        "is NOT a contradiction.\n"
        "- You must be CONSERVATIVE: only flag genuine contradictions.\n\n"
        "For each contradiction found, output EXACTLY one line in this format:\n"
        "VIOLATION|<dogma_id>|<brief explanation>\n\n"
        "If no contradictions are found, output EXACTLY:\n"
        "NO_VIOLATIONS\n\n"
        "After the violation lines (or NO_VIOLATIONS), output a final line:\n"
        "CONFIDENCE|<float between 0.0 and 1.0>\n"
        "indicating your confidence in the overall assessment.\n\n"
        "Do not output anything else."
    )

    def __init__(
        self,
        *,
        model: str = "gpt-4o",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        dogmas: list[dict[str, str]] | None = None,
    ) -> None:
        """
        Args:
            model: OpenAI model identifier.
            temperature: Low temperature for consistent classification.
            max_tokens: Maximum tokens for response.
            dogmas: Optional custom list of dogmas; defaults to the canonical 47.
        """
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self._dogmas = dogmas or DOGMAS

    async def guard(self, content: str) -> dict[str, Any]:
        """
        Check content against all key Catholic dogmas.

        CRITICAL: If any violation is detected, content is rejected entirely.

        Args:
            content: The content to check.

        Returns:
            Dict with keys:
                - ``passed`` (bool): True if no violations detected.
                - ``violations`` (list[str]): List of violation descriptions.
                - ``confidence`` (float): Classifier confidence in [0.0, 1.0].
        """
        logger.info(
            "[%s] Running doctrine guard check against %d dogmas",
            self.AGENT_ID,
            len(self._dogmas),
        )

        dogma_listing = self._format_dogmas()
        user_prompt = (
            f"DOGMAS TO CHECK AGAINST:\n{dogma_listing}\n\n"
            f"CONTENT TO EVALUATE:\n{content}"
        )

        try:
            response = await self._llm.ainvoke([
                SystemMessage(content=self._SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ])
            raw = response.content
        except Exception:
            logger.exception("[%s] LLM call failed during doctrine check", self.AGENT_ID)
            # Fail closed: if we cannot verify, reject
            return {
                "passed": False,
                "violations": [
                    "Doctrine check could not be completed due to a system error. "
                    "Content is held for manual review."
                ],
                "confidence": 0.0,
            }

        violations = self._parse_violations(raw)
        confidence = self._parse_confidence(raw)
        passed = len(violations) == 0

        if not passed:
            logger.warning(
                "[%s] DOCTRINE VIOLATION DETECTED: %d violation(s) found",
                self.AGENT_ID,
                len(violations),
            )
            for v in violations:
                logger.warning("[%s]   - %s", self.AGENT_ID, v)
        else:
            logger.info("[%s] Doctrine check PASSED", self.AGENT_ID)

        return {
            "passed": passed,
            "violations": violations,
            "confidence": confidence,
        }

    def _format_dogmas(self) -> str:
        """Format the dogma list for inclusion in the LLM prompt."""
        lines: list[str] = []
        for d in self._dogmas:
            lines.append(
                f"[{d['id']}] {d['label']} ({d['category']}): {d['desc']}"
            )
        return "\n".join(lines)

    @staticmethod
    def _parse_violations(response: str) -> list[str]:
        """Parse the LLM response for violation markers."""
        response = response.strip()

        if response.upper().startswith("NO_VIOLATIONS"):
            return []

        violations: list[str] = []
        for line in response.split("\n"):
            line = line.strip()
            if line.upper().startswith("VIOLATION|"):
                parts = line.split("|", maxsplit=2)
                if len(parts) >= 3:
                    dogma_id = parts[1].strip()
                    explanation = parts[2].strip()
                    violations.append(f"[{dogma_id}] {explanation}")
                elif len(parts) == 2:
                    violations.append(f"[{parts[1].strip()}] Unspecified violation")

        # If response didn't match expected format but also didn't say
        # NO_VIOLATIONS, treat as uncertain and fail closed.
        if not violations and "NO_VIOLATIONS" not in response.upper():
            logger.warning(
                "[A-021] Unexpected response format from LLM; failing closed."
            )
            violations.append(
                "Unable to parse doctrine check response; "
                "content held for manual review."
            )

        return violations

    @staticmethod
    def _parse_confidence(response: str) -> float:
        """Extract the confidence score from the LLM response."""
        for line in response.strip().split("\n"):
            line = line.strip()
            if line.upper().startswith("CONFIDENCE|"):
                parts = line.split("|", maxsplit=1)
                if len(parts) == 2:
                    try:
                        return max(0.0, min(1.0, float(parts[1].strip())))
                    except ValueError:
                        pass
        # Default confidence if not parseable
        return 0.9 if "NO_VIOLATIONS" in response.upper() else 0.5
