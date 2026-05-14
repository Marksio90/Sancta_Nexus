# Wizja produktowa — Sancta Nexus

## Czym jest Sancta Nexus

Sancta Nexus to katolicka platforma modlitwy i formacji duchowej, która pomaga użytkownikowi:

- codziennie modlić się Słowem Bożym (Lectio Divina),
- prowadzić dziennik duchowy,
- przechodzić przez programy rekolekcyjne,
- zapisywać intencje modlitewne,
- korzystać z bezpiecznego Asystenta refleksji,
- rozwijać nawyk regularnej modlitwy i formacji.

## Czym NIE jest

- Nie jest AI-kierownikiem duchowym.
- Nie jest AI-spowiednikiem ani AI-księdzem.
- Nie zastępuje kapłana, spowiedzi, sakramentów ani realnej wspólnoty.
- Nie rozstrzyga o stanie łaski ani woli Bożej.
- Nie zastępuje terapeuty.

---

## Użytkownik docelowy

**Główny użytkownik:** Katolik praktykujący, który chce modlić się regularnie, ale nie zawsze wie jak zacząć lub jak wrócić po przerwie.

**Dodatkowe grupy:**
- Osoby szukające narzędzia do codziennej formacji
- Wspólnoty, grupy modlitewne, duszpasterstwa
- Osoby przygotowujące się do sakramentów
- Parafie szukające narzędzia dla grup

---

## Wartości produktowe

| Wartość | Co oznacza w praktyce |
|---|---|
| Spokój | UI minimalistyczny, bez agresywnych CTA |
| Pokora AI | Asystent nie jest autorytetem, odsyła do człowieka |
| Prywatność | Dziennik jest prywatny domyślnie, można usunąć dane |
| Modularność | Każdy moduł można włączyć lub wyłączyć |
| Zatwierdzalne treści | Każda treść ma status i przechodzi przez review |
| Bezpieczeństwo | Każda odpowiedź AI przechodzi przez safety layer |

---

## Architektura modułowa

System jest zbudowany jako Core Platform + moduły funkcjonalne.

Każdy moduł ma:
- jasny cel (co pomaga użytkownikowi zrobić),
- granice odpowiedzialności (czego nie robi),
- feature flag (może być wyłączony),
- status (planned / experimental / beta / stable),
- safety rules (szczególnie dla modułów wrażliwych).

---

## Monetyzacja (docelowa)

| Model | Co zawiera |
|---|---|
| Free | Podstawowa Lectio Divina, ograniczona historia, wybrane modlitwy |
| Premium | Pełna historia, eksport, zaawansowany Asystent refleksji, programy premium |
| Organizacja / B2B | Panel grupy, wspólne programy, prowadzący, intencje wspólnotowe |

---

## Nadrzędna zasada

> Najpierw stabilność. Potem modułowość. Potem UX. Potem AI. Potem monetyzacja. Nigdy odwrotnie.
