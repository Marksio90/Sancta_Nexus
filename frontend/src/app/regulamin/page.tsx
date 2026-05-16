import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Regulamin — Sancta Nexus",
  description: "Warunki korzystania z platformy Sancta Nexus.",
};

const LAST_UPDATED = "15 maja 2026";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold text-[#d4af37] mb-3">{title}</h2>
      <div className="text-gray-300 leading-relaxed space-y-3 text-sm">{children}</div>
    </section>
  );
}

export default function RegulaminPage() {
  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white">
      <div className="max-w-2xl mx-auto px-4 py-12 pb-24">
        <div className="text-center mb-10">
          <div className="text-4xl mb-4">📜</div>
          <h1 className="text-2xl font-bold text-[#d4af37] mb-2">Regulamin</h1>
          <p className="text-xs text-gray-600">Ostatnia aktualizacja: {LAST_UPDATED}</p>
        </div>

        {/* Najważniejsze zastrzeżenie — na górze, widoczne */}
        <div className="bg-red-900/10 border border-red-700/30 rounded-2xl p-5 mb-8">
          <p className="text-sm text-red-200 font-medium mb-1">⚠ Ważne zastrzeżenie</p>
          <p className="text-sm text-gray-300 leading-relaxed">
            Sancta Nexus <strong className="text-white">nie jest i nie zastępuje</strong> kapłana,
            spowiednika, kierownika duchowego ani psychologa. Asystent AI pomaga porządkować myśli
            i wracać do modlitwy — nie udziela rozgrzeszenia, nie ocenia stanu łaski,
            nie diagnozuje psychicznie i nie zastępuje terapii.
            W sytuacji kryzysu psychicznego lub myśli samobójczych zadzwoń na
            <strong className="text-white"> Telefon Zaufania: 116 123</strong>.
          </p>
        </div>

        <Section title="1. Definicje">
          <ul className="list-disc list-inside space-y-1.5">
            <li><strong className="text-white">Platforma</strong> — serwis internetowy i aplikacja mobilna Sancta Nexus</li>
            <li><strong className="text-white">Użytkownik</strong> — osoba korzystająca z Platformy po założeniu konta</li>
            <li><strong className="text-white">Plan Free</strong> — bezpłatny dostęp z ograniczonymi funkcjami</li>
            <li><strong className="text-white">Plan Premium</strong> — płatna subskrypcja z pełnym dostępem</li>
            <li><strong className="text-white">Asystent AI</strong> — narzędzie refleksji opartej na sztucznej inteligencji</li>
          </ul>
        </Section>

        <Section title="2. Warunki korzystania">
          <p>Korzystanie z Platformy wymaga:</p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>Ukończenia 16 lat (lub zgody rodzica/opiekuna dla osób młodszych)</li>
            <li>Rejestracji z prawdziwymi danymi</li>
            <li>Akceptacji niniejszego Regulaminu i Polityki Prywatności</li>
          </ul>
        </Section>

        <Section title="3. Charakter Asystenta AI — ograniczenia">
          <p>Asystent refleksji w Sancta Nexus:</p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>Pomaga <em>porządkować myśli</em> i wracać do modlitwy</li>
            <li>Nie jest kapłanem — nie udziela rozgrzeszenia ani sakramentów</li>
            <li>Nie jest spowiednikiem — nie ocenia grzechów ani stanu łaski</li>
            <li>Nie jest kierownikiem duchowym — nie zastępuje relacji z żywym człowiekiem</li>
            <li>Nie jest terapeutą — nie diagnozuje zaburzeń psychicznych</li>
            <li>Może popełniać błędy — zawsze weryfikuj treści teologiczne z kapłanem</li>
          </ul>
          <p>
            Każda odpowiedź AI zawiera stosowne zastrzeżenie. Operator zastrzega prawo do
            blokowania zapytań dotyczących spowiedzi, rozgrzeszenia lub diagnozy psychologicznej.
          </p>
        </Section>

        <Section title="4. Plan Free — zakres usług">
          <ul className="list-disc list-inside space-y-1.5">
            <li>Różaniec — 20 tajemnic bez medytacji AI</li>
            <li>Brewiarz (Liturgia Godzin)</li>
            <li>Dziennik duchowy — do 3 wpisów miesięcznie</li>
            <li>Intencje modlitewne i grupy</li>
            <li>Przeglądanie sesji wspólnotowych</li>
          </ul>
        </Section>

        <Section title="5. Plan Premium — subskrypcja">
          <p>Plan Premium aktywowany jest po zrealizowaniu płatności przez Stripe.</p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>Subskrypcja odnawia się automatycznie (miesięcznie lub rocznie)</li>
            <li>Anulowanie możliwe w dowolnym momencie — dostęp do końca okresu rozliczeniowego</li>
            <li>14-dniowy okres na zwrot pieniędzy — wystarczy napisać do nas</li>
            <li>Ceny mogą ulec zmianie — powiadomimy 30 dni wcześniej</li>
          </ul>
        </Section>

        <Section title="6. Zasady zachowania">
          <p>Zabrania się:</p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>Używania Platformy do działań niezgodnych z prawem</li>
            <li>Publikowania treści obraźliwych, bluźnierczych lub szerzących nienawiść</li>
            <li>Podszywania się pod innych użytkowników lub instytucje kościelne</li>
            <li>Prób obejścia systemów bezpieczeństwa lub ograniczeń AI</li>
            <li>Używania Platformy do celów komercyjnych bez pisemnej zgody</li>
          </ul>
        </Section>

        <Section title="7. Moderacja intencji modlitewnych">
          <p>
            Intencje modlitewne publikowane publicznie podlegają moderacji.
            Moderatorzy mogą usuwać treści naruszające zasady wspólnoty lub dobre obyczaje
            bez wcześniejszego powiadomienia.
          </p>
        </Section>

        <Section title="8. Własność intelektualna">
          <p>
            Treści generowane przez AI na Twoje żądanie są Twoją własnością
            (w zakresie dozwolonym przez prawo). Elementy interfejsu, kod i projekt graficzny
            są własnością Operatora i nie mogą być kopiowane bez zgody.
          </p>
        </Section>

        <Section title="9. Odpowiedzialność">
          <p>
            Platforma jest udostępniana „tak jak jest&rdquo;. Operator nie odpowiada za decyzje
            podejmowane na podstawie treści wygenerowanych przez AI. Za decyzje duchowe
            odpowiada Użytkownik — ostatecznym autorytetem jest nauczanie Kościoła Katolickiego
            i żywy duszpasterz.
          </p>
        </Section>

        <Section title="10. Zmiany regulaminu">
          <p>
            O zmianach regulaminu poinformujemy e-mailem i powiadomieniem w aplikacji
            co najmniej 14 dni przed wejściem w życie. Dalsze korzystanie z Platformy
            oznacza akceptację nowych warunków.
          </p>
        </Section>

        <Section title="11. Prawo właściwe">
          <p>
            Niniejszy regulamin podlega prawu polskiemu. Spory rozstrzygane są przez sądy
            powszechne właściwe dla siedziby Operatora, z możliwością mediacji pozasądowej.
          </p>
        </Section>

        <div className="border-t border-white/10 pt-6 mt-8 text-center">
          <div className="flex justify-center gap-4 text-xs text-gray-600">
            <a href="/polityka-prywatnosci" className="hover:text-[#d4af37] transition-colors">Polityka Prywatności</a>
            <span>·</span>
            <a href="mailto:marks.mateusz@wp.pl" className="hover:text-[#d4af37] transition-colors">Kontakt</a>
          </div>
        </div>
      </div>
    </main>
  );
}
