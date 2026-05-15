import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Polityka Prywatności — Sancta Nexus",
  description: "Informacje o przetwarzaniu danych osobowych w platformie Sancta Nexus.",
};

const LAST_UPDATED = "15 maja 2026";
const CONTACT_EMAIL = "prywatnosc@sanctanexus.org";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold text-[#d4af37] mb-3">{title}</h2>
      <div className="text-gray-300 leading-relaxed space-y-3 text-sm">{children}</div>
    </section>
  );
}

export default function PolitykaPrywatnosciPage() {
  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white">
      <div className="max-w-2xl mx-auto px-4 py-12 pb-24">
        <div className="text-center mb-10">
          <div className="text-4xl mb-4">🔒</div>
          <h1 className="text-2xl font-bold text-[#d4af37] mb-2">Polityka Prywatności</h1>
          <p className="text-xs text-gray-600">Ostatnia aktualizacja: {LAST_UPDATED}</p>
        </div>

        <div className="bg-[#d4af37]/5 border border-[#d4af37]/20 rounded-2xl p-4 mb-8 text-sm text-gray-400">
          Sancta Nexus szanuje Twoją prywatność. Ta polityka wyjaśnia, jakie dane gromadzimy,
          w jakim celu i jakie masz prawa jako użytkownik.
        </div>

        <Section title="1. Administrator danych">
          <p>
            Administratorem Twoich danych osobowych jest operator platformy Sancta Nexus
            (dalej: &bdquo;my&rdquo;, &bdquo;Administrator&rdquo;).
            Kontakt w sprawach prywatności: <strong className="text-white">{CONTACT_EMAIL}</strong>
          </p>
        </Section>

        <Section title="2. Jakie dane zbieramy">
          <p><strong className="text-white">Dane rejestracyjne:</strong> adres e-mail, imię (wyświetlane). Niezbędne do założenia konta.</p>
          <p><strong className="text-white">Dziennik duchowy:</strong> treści wpisów, które sam wprowadzasz. Przechowywane zaszyfrowane. Nie są czytane przez pracowników.</p>
          <p><strong className="text-white">Aktywność modlitewna:</strong> liczba sesji, wybrane praktyki, czas korzystania z aplikacji (dane agregowane).</p>
          <p><strong className="text-white">Metadane AI:</strong> typ interakcji, kategoria ryzyka bezpieczeństwa — bez treści rozmowy.</p>
          <p><strong className="text-white">Dane rozliczeniowe:</strong> przetwarzane wyłącznie przez Stripe. Nie przechowujemy numerów kart.</p>
          <p><strong className="text-white">Dane techniczne:</strong> adres IP, typ urządzenia, wersja systemu operacyjnego — wyłącznie do diagnostyki.</p>
          <p>
            <strong className="text-white">Czego NIE zbieramy:</strong> lokalizacji GPS, kontaktów,
            treści Twoich modlitw przekazywanych do AI (system usuwa je po przetworzeniu).
          </p>
        </Section>

        <Section title="3. Cel i podstawa przetwarzania">
          <ul className="list-disc list-inside space-y-1.5">
            <li>Świadczenie usług platformy — <em>art. 6 ust. 1 lit. b RODO</em> (wykonanie umowy)</li>
            <li>Obsługa płatności i subskrypcji — <em>art. 6 ust. 1 lit. b RODO</em></li>
            <li>Bezpieczeństwo i wykrywanie nadużyć — <em>art. 6 ust. 1 lit. f RODO</em> (uzasadniony interes)</li>
            <li>Powiadomienia push (jeśli wyraziłeś zgodę) — <em>art. 6 ust. 1 lit. a RODO</em></li>
            <li>Obowiązki prawne — <em>art. 6 ust. 1 lit. c RODO</em></li>
          </ul>
        </Section>

        <Section title="4. Podmioty przetwarzające dane (procesorzy)">
          <p>Powierzamy dane następującym podmiotom:</p>
          <ul className="list-disc list-inside space-y-1.5">
            <li><strong className="text-white">OpenAI, L.L.C.</strong> — przetwarzanie tekstu przez AI (API); dane nie są używane do trenowania modeli</li>
            <li><strong className="text-white">Stripe, Inc.</strong> — obsługa płatności i subskrypcji</li>
            <li><strong className="text-white">Dostawca hostingu</strong> — infrastruktura serwerowa w UE lub z odpowiednimi gwarancjami (SCCs)</li>
          </ul>
          <p>Nie sprzedajemy Twoich danych podmiotom trzecim.</p>
        </Section>

        <Section title="5. Twoje prawa (RODO)">
          <ul className="list-disc list-inside space-y-1.5">
            <li><strong className="text-white">Dostęp</strong> — możesz w każdej chwili pobrać kopię swoich danych (Moje konto → Eksport danych)</li>
            <li><strong className="text-white">Sprostowanie</strong> — możesz edytować imię w ustawieniach konta</li>
            <li><strong className="text-white">Usunięcie</strong> — możesz usunąć konto (Moje konto → Usuń konto); dane są usuwane w ciągu 30 dni</li>
            <li><strong className="text-white">Przenoszenie</strong> — eksport w formacie JSON jest dostępny na żądanie</li>
            <li><strong className="text-white">Sprzeciw</strong> — możesz wycofać zgodę na powiadomienia w ustawieniach urządzenia</li>
            <li><strong className="text-white">Skarga</strong> — masz prawo złożyć skargę do Prezesa UODO (Urząd Ochrony Danych Osobowych)</li>
          </ul>
        </Section>

        <Section title="6. Ochrona danych szczególnie wrażliwych">
          <p>
            Twoje wpisy w dzienniku duchowym mogą zawierać dane dotyczące przekonań religijnych
            — kategorię szczególnie wrażliwą w rozumieniu art. 9 RODO.
            Przetwarzamy je wyłącznie na podstawie Twojej wyraźnej zgody (konto) i przechowujemy
            w postaci zaszyfrowanej. Nikt z personelu nie czyta tych treści.
          </p>
          <p>
            Funkcja AI może opcjonalnie analizować wpisy dziennika — wyłącznie gdy wyrazisz na to
            zgodę w ustawieniach prywatności konta. Domyślnie: wyłączona.
          </p>
        </Section>

        <Section title="7. Retencja danych">
          <p>Przechowujemy dane przez czas aktywności konta. Po usunięciu konta:</p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>Dane profilu i dziennik: usunięte w ciągu 30 dni</li>
            <li>Dane rozliczeniowe: przechowywane 5 lat (obowiązek podatkowy)</li>
            <li>Logi bezpieczeństwa: 90 dni</li>
          </ul>
        </Section>

        <Section title="8. Pliki cookie i dane lokalne">
          <p>
            Nie używamy analitycznych plików cookie ani śledzenia reklamowego.
            Aplikacja korzysta z <code className="text-[#d4af37] bg-white/5 px-1 rounded">localStorage</code> do przechowywania
            tokenu sesji i preferencji onboardingu — wyłącznie lokalnie na Twoim urządzeniu.
          </p>
        </Section>

        <Section title="9. Transfery danych poza EOG">
          <p>
            OpenAI i Stripe mają siedzibę w USA. Transfery są zabezpieczone
            Standardowymi Klauzulami Umownymi (SCCs) zatwierdzonymi przez Komisję Europejską.
          </p>
        </Section>

        <Section title="10. Zmiany polityki">
          <p>
            O istotnych zmianach poinformujemy e-mailem lub powiadomieniem w aplikacji
            co najmniej 14 dni przed wejściem w życie.
          </p>
        </Section>

        <div className="border-t border-white/10 pt-6 mt-8 text-center">
          <p className="text-xs text-gray-600">
            Pytania? Napisz do nas: <a href={`mailto:${CONTACT_EMAIL}`} className="text-[#d4af37] hover:underline">{CONTACT_EMAIL}</a>
          </p>
          <p className="text-xs text-gray-700 mt-2">
            Sancta Nexus nie zastępuje kapłana, spowiednika ani kierownika duchowego.
          </p>
        </div>
      </div>
    </main>
  );
}
