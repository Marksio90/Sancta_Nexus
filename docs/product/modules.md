# Moduły platformy — Sancta Nexus

## Cykl statusów

```
planned → experimental → beta → stable → disabled
```

- **planned** — zaprojektowany, kod może istnieć, niedostępny dla użytkownika
- **experimental** — dostępny tylko dla adminów, testowany aktywnie
- **beta** — dostępny dla wybranych użytkowników, monitorowany
- **stable** — dostępny dla wszystkich, pełna funkcjonalność
- **disabled** — wyłączony (zachowany w kodzie)

Każdy moduł ma feature flag w `.env`. Wyłączenie flagi ukrywa moduł w UI i zwraca HTTP 503 z API.

---

## Moduły stabilne

### `lectio-divina` — Lectio Divina

**Status:** stable  
**Feature flag:** `FEATURE_LECTIO_DIVINA`

Flow 5-etapowy:
1. Lectio — przeczytaj fragment
2. Meditatio — rozważ
3. Oratio — odpowiedz modlitwą
4. Contemplatio — trwaj w ciszy
5. Actio — wybierz owoc dnia

AI może: generować pytania do refleksji, sugerować modlitwę, podsumować notatkę.  
AI nie może: narzucać interpretacji jako jedynej właściwej.

---

### `bible` — Biblia interaktywna

**Status:** stable  
**Feature flag:** `FEATURE_BIBLE`

Przeglądanie ksiąg, wyszukiwanie fragmentów, ulubione, historia czytania, notatki.

AI (`Asystent rozważania Słowa`): pytania do fragmentu, kontekst, propozycja modlitwy.  
AI nie może: prezentować niezweryfikowanych interpretacji jako nauki Kościoła.

---

## Moduły beta

### `prayer-journal` — Dziennik duchowy

**Status:** beta  
**Feature flag:** `FEATURE_PRAYER_JOURNAL`

Wpisy dziennika, tagi, nastrój/ton refleksji, powiązanie z Lectio Divina i programem.  
Prywatny domyślnie. Możliwość eksportu i usunięcia.

AI (`Asystent refleksji`): podsumowanie wpisu, pytania pogłębiające, propozycja modlitwy.

---

### `breviary` — Liturgia Godzin

**Status:** beta  
**Feature flag:** `FEATURE_BREVIARY`

Modlitwa poranna (Jutrznia), wieczorna (Nieszpory), Kompleta. Liturgiczny fragment dnia.

---

## Moduły experimental

### `reflection-assistant` — Asystent refleksji

**Status:** experimental  
**Feature flag:** `FEATURE_REFLECTION_ASSISTANT`  
**API prefix:** `/api/v1/reflection-assistant`  
**Wewnętrzny plik (do rename w Phase 2):** `spiritual_director.py`

Rozmowa po sesji modlitewnej. Pytania pomocnicze, propozycja modlitwy, podsumowanie refleksji, zachęta do rozmowy z realną osobą.

**Ważne:** Każda odpowiedź przechodzi przez `AISafetyLayer`. Nie używa nazwy „Kierownik duchowy AI".

---

### `prayer-intentions` — Intencje modlitewne

**Status:** experimental  
**Feature flag:** `FEATURE_PRAYER_INTENTIONS`

Prywatne i wspólnotowe intencje. Intencje publiczne wymagają moderacji.

---

### `sacramental-prep` — Przewodnik przygotowania

**Status:** experimental  
**Feature flag:** `FEATURE_SACRAMENTAL_PREP`

Materiały edukacyjne i organizacyjne do sakramentów. **Nie zastępuje parafii ani rozmowy z kapłanem.** Nie decyduje o dopuszczeniu do sakramentu.

---

## Moduły planned

### `communities` — Wspólnoty

**Status:** planned  
**Feature flag:** `FEATURE_COMMUNITIES`

Grupy, parafie, duszpasterstwa. Role: member, group_leader, moderator, organization_admin.  
Podstawa modelu B2B.

---

### `retreat-programs` — Programy rekolekcyjne

**Status:** planned  
**Feature flag:** `FEATURE_RETREAT_PROGRAMS`

Programy 3/7/14/30 dni, Adwent, Wielki Post, Nowenna. Panel redakcyjny z workflow zatwierdzania.  
Główny moduł zarobkowy.

---

### `spiritual-dashboard` — Panel duchowy

**Status:** planned  
**Feature flag:** `FEATURE_SPIRITUAL_DASHBOARD`

Historia praktyki, aktualny program, ostatnie wpisy, intencje, ulubione fragmenty.  
Bez agresywnej gamifikacji — spokojna historia, łagodne przypomnienia.

---

### `content-library` — Biblioteka duchowa

**Status:** planned  
**Feature flag:** `FEATURE_CONTENT_LIBRARY`

Artykuły, modlitwy, rozważania, cytaty, dokumenty. Workflow: draft → review → approved → published.

---

### `examination-of-conscience` — Pomocnik rachunku sumienia

**Status:** planned  
**Feature flag:** `FEATURE_EXAMINATION_OF_CONSCIENCE`  
**Safety level:** Wysoki

Rachunek według przykazań/cnót. Tryb bez zapisu. Prywatne notatki z możliwością usunięcia.  
AI nie orzeka o grzechu ciężkim. Nie prowadzi spowiedzi.

---

### `discernment-notebook` — Notatnik rozeznawania

**Status:** planned  
**Feature flag:** `FEATURE_DISCERNMENT_NOTEBOOK`  
**Safety level:** Wysoki

Porządkowanie myśli wokół ważnych decyzji. AI zadaje pytania, nie podejmuje decyzji.  
AI nie twierdzi, że zna wolę Bożą.
