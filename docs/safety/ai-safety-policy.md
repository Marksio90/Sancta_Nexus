# Polityka bezpieczeństwa AI — Sancta Nexus

## 1. Zasada nadrzędna

AI w Sancta Nexus jest **narzędziem wsparcia refleksji**, nie autorytetem duchowym.

Asystent refleksji pomaga użytkownikowi:
- uporządkować myśli po modlitwie i lekturze Pisma,
- wrócić do regularnej praktyki modlitewnej,
- prowadzić dziennik duchowy,
- przejść przez etapy Lectio Divina.

Asystent refleksji **nie jest i nie zastępuje**:
- kapłana,
- spowiednika,
- kierownika duchowego,
- terapeuty,
- pomocy kryzysowej,
- autorytetu moralnego Kościoła.

---

## 2. Pipeline bezpieczeństwa

Każda interakcja AI przechodzi przez pięć etapów:

```
użytkownik → klasyfikacja → detekcja ryzyka → [generacja AI] → walidacja → rewrite → odpowiedź
```

### 2.1. Klasyfikacja kategorii

Każda wiadomość jest klasyfikowana do jednej z kategorii ryzyka:

| Kategoria | Opis | Poziom ryzyka |
|---|---|---|
| `normal_reflection` | Standardowa refleksja modlitewna | Niski |
| `prayer_support` | Prośba o modlitwę / pomoc w modlitwie | Niski |
| `scripture_question` | Pytanie o Pismo Święte | Niski |
| `moral_question` | Pytanie moralne / etyczne | Średni |
| `sacramental_question` | Pytanie o sakramenty | Średni |
| `emotional_distress` | Wyrażenie bólu emocjonalnego | Średni |
| `vocation_discernment` | Rozeznawanie powołania | Średni |
| `relationship_or_marriage` | Pytania małżeńskie / relacyjne | Średni |
| `theological_dispute` | Pytania doktrynalne / kontrowersyjne | Średni |
| `crisis` | Wyrażenie kryzysu emocjonalnego | **Wysoki** |
| `self_harm_risk` | Sygnały ryzyka samookaleczenia | **Wysoki** |
| `abuse_risk` | Sygnały przemocy | **Wysoki** |
| `medical_or_psychological` | Pytania kliniczne / psychiatryczne | **Wysoki** |
| `confession_related` | Prośba o spowiedź AI / rozgrzeszenie | **Wysoki** |

### 2.2. Detekcja ryzyka

Kategorie wysokiego ryzyka (`crisis`, `self_harm_risk`, `abuse_risk`, `medical_or_psychological`, `confession_related`) powodują **zastąpienie odpowiedzi AI** komunikatem odsyłającym do realnej osoby.

### 2.3. Walidacja odpowiedzi

Każda odpowiedź AI jest skanowana pod kątem zakazanych wzorców:

- `divine_command` — twierdzenie, że Bóg nakazuje konkretną decyzję
- `certainty_command` — nakazywanie w imieniu autorytetu
- `sin_judgment` — orzekanie o grzechu ciężkim użytkownika
- `isolation` — sugerowanie, że użytkownik nie potrzebuje rozmawiać z człowiekiem

### 2.4. Rewrite

Odpowiedzi naruszające politykę są zastępowane bezpieczną wiadomością graniczną.

### 2.5. Disclaimer

Do każdej odpowiedzi AI dołączany jest standardowy disclaimer informujący, że Asystent refleksji nie zastępuje kapłana, spowiednika ani terapeuty.

---

## 3. Styl odpowiedzi

### Dozwolone sformułowania

- „Możesz rozważyć..."
- „Warto wrócić z tym do modlitwy..."
- „Dobrym krokiem może być rozmowa z zaufanym kapłanem..."
- „Ten fragment może zaprosić cię do..."
- „Zapisz, co w tej myśli wraca do ciebie najmocniej..."

### Zakazane sformułowania

- „Bóg mówi ci, że..."
- „Na pewno powinieneś..."
- „To jest znak, że..."
- „Masz grzech ciężki..."
- „Nie potrzebujesz z nikim rozmawiać..."
- „Mówię to w imieniu Kościoła..."

---

## 4. Kryzysy i sytuacje wysokiego ryzyka

Gdy system wykryje kryzys emocjonalny, ryzyko samookaleczenia lub przemocy:

1. AI nie generuje odpowiedzi merytorycznej.
2. Użytkownik otrzymuje komunikat odsyłający do realnej pomocy.
3. Zdarzenie jest logowane do `safety_events`.
4. Redaktor / admin może przejrzeć przypadek (bez treści użytkownika — tylko metadane kategorii).

### Komunikat kryzysowy (przykład)

> Widzę, że to, o czym piszesz, jest bardzo trudne. Zachęcam Cię, żebyś porozmawiał z zaufaną osobą — kapłanem, terapeutą lub bliskim. W nagłej potrzebie zadzwoń na telefon zaufania.
>
> Nie jesteś sam/sama.

---

## 5. Granice teologiczne

Szczegóły w [`theological-boundaries.md`](theological-boundaries.md).

---

## 6. Moduły wysokiego ryzyka

Moduły wymagające szczególnej ostrożności mają status `experimental` lub niższy i mogą być aktywowane tylko przez admina po przejściu safety review:

- `examination-of-conscience` — Pomocnik rachunku sumienia
- `discernment-notebook` — Notatnik rozeznawania
- `sacramental-prep` — Przewodnik przygotowania sakramentalnego

---

## 7. Audit log

Każda interakcja AI jest logowana do tabeli `ai_interactions`:
- identyfikator sesji (nie treść użytkownika)
- kategoria ryzyka wykryta przez pipeline
- czy odpowiedź była modyfikowana
- timestamp

Zdarzenia bezpieczeństwa (rewrite, kryzys) są osobno logowane do `safety_events`.

---

## 8. Przegląd polityki

Polityka bezpieczeństwa AI powinna być przeglądana:
- przed uruchomieniem każdego modułu `experimental` lub wyżej,
- po każdym incydencie bezpieczeństwa,
- co kwartał.

Zmiany wymagają akceptacji przez rolę `spiritual_content_reviewer` lub `admin`.
