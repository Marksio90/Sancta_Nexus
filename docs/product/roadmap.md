# Roadmapa implementacji — Sancta Nexus

## Phase 1 — Stabilizacja repo ✅ W toku

**Cel:** Projekt się uruchamia, README mówi prawdę, moduły mają statusy.

Zadania:
- [x] Pełne README.md
- [x] Feature flags (`.env.example`, `config.py`, `feature_flags.py`)
- [x] Warstwa bezpieczeństwa AI (`safety.py`)
- [x] Bezpieczne nazwy API (prefix `/api/v1/reflection-assistant`)
- [x] Dokumentacja (`docs/safety/`, `docs/product/`, `docs/architecture/`)
- [ ] Testy jednostkowe dla `feature_flags.py` i `safety.py`
- [ ] CI/CD (GitHub Actions: lint, test, build)

**Rezultat:** Wiadomo co jest aktywne, wiadomo co jest eksperymentalne, README mówi prawdę.

---

## Phase 2 — Core Platform

**Cel:** Stabilny fundament użytkowników, ról i logowania.

Zadania:
- [ ] Rozbudowa modeli: `user_profiles`, `audit_logs`, `feature_flags` (tabela DB)
- [ ] System ról: user, premium_user, moderator, editor, spiritual_content_reviewer, admin, organization_admin, group_leader
- [ ] Ustawienia prywatności użytkownika
- [ ] Audit log (każda ważna operacja)
- [ ] Eksport danych użytkownika
- [ ] Usunięcie danych (GDPR)
- [ ] Podstawowy panel admina
- [ ] Rename wewnętrzny: `spiritual_director.py` → `reflection_assistant.py`

---

## Phase 3 — Lectio Divina + Dziennik duchowy

**Cel:** Pierwszy realny produkt codziennego użycia.

Zadania:
- [ ] Pełne flow 5-etapowe Lectio Divina z zapisem do dziennika
- [ ] Historia sesji i kontynuacja przerwanej sesji
- [ ] Ulubione fragmenty
- [ ] Eksport sesji do PDF
- [ ] Dziennik duchowy z tagami i wyszukiwaniem
- [ ] Asystent refleksji z safety layer (zintegrowany)
- [ ] Testy safety dla Asystenta refleksji

---

## Phase 4 — Biblia + Biblioteka treści + RAG

**Cel:** AI odpowiada na źródłach, nie z pamięci modelu.

Zadania:
- [ ] Pełna baza fragmentów biblijnych
- [ ] Wyszukiwarka z paginacją
- [ ] Notatki do fragmentów
- [ ] Tematyczne listy fragmentów
- [ ] Biblioteka treści z workflow zatwierdzania
- [ ] RAG grounding na Piśmie i KKK
- [ ] Źródła w odpowiedziach AI

---

## Phase 5 — Programy rekolekcyjne

**Cel:** Pierwszy realny moduł zarobkowy.

Zadania:
- [ ] Programy 7/14/30 dni
- [ ] Panel redakcyjny (draft → review → approved → published)
- [ ] Śledzenie postępu
- [ ] Przypomnienia
- [ ] Programy darmowe i premium
- [ ] Integracja płatności

---

## Phase 6 — Intencje + Wspólnoty

**Cel:** Fundament pod B2B i parafie/wspólnoty.

Zadania:
- [ ] Intencje prywatne i wspólnotowe
- [ ] Moderacja intencji publicznych
- [ ] Grupy modlitewne (tworzenie, zaproszenia, role)
- [ ] Wspólne programy rekolekcyjne
- [ ] Panel prowadzącego
- [ ] Plan B2B (organizacje, parafie)

---

## Phase 7 — Moduły wrażliwe

**Cel:** Funkcje wysokiej wartości, ale pod pełną kontrolą safety.

Zadania:
- [ ] Pomocnik rachunku sumienia (tryb bez zapisu, usuwanie po sesji)
- [ ] Przewodnik przygotowania sakramentalnego (pełny zakres)
- [ ] Notatnik rozeznawania
- [ ] Rozbudowane safety tests dla tych modułów
- [ ] Safety review przed aktywacją

---

## Phase 8 — Monetyzacja

**Cel:** Platforma gotowa do zarabiania.

Zadania:
- [ ] Plan Free / Premium
- [ ] Subskrypcja miesięczna i roczna
- [ ] Dostęp organizacyjny (B2B)
- [ ] Limity dla Free
- [ ] Panel billingowy
- [ ] Jednorazowy zakup rekolekcji

---

## Zasada priorytetów

> Najpierw stabilność. Potem modułowość. Potem UX. Potem AI. Potem monetyzacja.
