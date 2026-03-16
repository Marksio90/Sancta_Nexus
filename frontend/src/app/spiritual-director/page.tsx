"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, ArrowLeft, AlertTriangle } from "lucide-react";
import Link from "next/link";

type Tradition =
  | "ignacjanska"
  | "karmelitanska"
  | "benedyktynska"
  | "franciszkanska";

interface Message {
  id: string;
  role: "user" | "director";
  content: string;
  timestamp: Date;
}

const TRADITIONS: { key: Tradition; label: string; description: string }[] = [
  {
    key: "ignacjanska",
    label: "Ignacjańska",
    description: "Rozeznawanie duchowe, Ćwiczenia Duchowe św. Ignacego",
  },
  {
    key: "karmelitanska",
    label: "Karmelitańska",
    description: "Modlitwa kontemplacyjna, św. Teresa z Ávili, św. Jan od Krzyża",
  },
  {
    key: "benedyktynska",
    label: "Benedyktyńska",
    description: "Ora et labora, Reguła św. Benedykta, Lectio Divina",
  },
  {
    key: "franciszkanska",
    label: "Franciszkańska",
    description: "Ubóstwo duchowe, radość, bliskość z naturą i stworzeniem",
  },
];

const MOCK_RESPONSES: Record<Tradition, string[]> = {
  ignacjanska: [
    "Dziękuję za podzielenie się tym ze mną. W tradycji ignacjańskiej, zwracamy szczególną uwagę na 'poruszenia duszy' — te wewnętrzne uczucia pocieszenia i strapienia. Opowiedz mi więcej: kiedy myślisz o tej sytuacji, czy czujesz pokój i radość (pocieszenie), czy raczej niepokój i smutek (strapienie)?",
    "To bardzo ważne spostrzeżenie. Św. Ignacy uczył, że Bóg przemawia do nas przez nasze pragnienia. Spróbujmy rozeznać razem: jakie jest Twoje najgłębsze pragnienie w tej chwili? Nie to powierzchowne, ale to, które pochodzi z głębi serca.",
  ],
  karmelitanska: [
    "W tradycji karmelitańskiej, św. Teresa z Ávili mówiła o modlitwie jako o 'rozmowie przyjaciół'. Zachęcam Cię, abyś po prostu stanął przed Bogiem taki, jaki jesteś, bez masek. Nie musisz szukać pięknych słów — wystarczy obecność.",
    "Św. Jan od Krzyża pisał o 'ciemnej nocy duszy' — okresach, gdy Bóg wydaje się odległy. Ale to nie jest Jego nieobecność — to zaproszenie do głębszej wiary, która wykracza poza uczucia. Czy doświadczasz teraz takiej ciemności?",
  ],
  benedyktynska: [
    "W duchu benedyktyńskim, zachęcam Cię do szukania Boga w zwyczajności dnia. Reguła św. Benedykta mówi: 'Ora et labora' — módl się i pracuj. Każda chwila może stać się modlitwą. Jak wygląda Twój codzienny rytm duchowy?",
    "Lectio Divina jest sercem duchowości benedyktyńskiej. Proponuję, abyś codziennie poświęcił choćby 15 minut na uważne czytanie Pisma Świętego. Nie chodzi o ilość przeczytanego tekstu, ale o głębię spotkania ze Słowem.",
  ],
  franciszkanska: [
    "Św. Franciszek widział Boga we wszystkim — w słońcu, w wodzie, w każdym stworzeniu. Zachęcam Cię: wyjdź dziś na zewnątrz i spójrz na świat oczami wiary. Gdzie dostrzegasz ślady Bożej obecności wokół siebie?",
    "Franciszek mówił: 'Głoście Ewangelię, a jeśli trzeba, użyjcie słów.' Twoje życie jest najpiękniejszym kazaniem. Jak możesz dziś być świadkiem radości Ewangelii w swoim otoczeniu?",
  ],
};

export default function SpiritualDirectorPage() {
  const [selectedTradition, setSelectedTradition] =
    useState<Tradition>("ignacjanska");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);

    // Simulate AI response
    setTimeout(() => {
      const responses = MOCK_RESPONSES[selectedTradition];
      const response = responses[messages.length % responses.length];

      const directorMessage: Message = {
        id: crypto.randomUUID(),
        role: "director",
        content: response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, directorMessage]);
      setIsTyping(false);
    }, 1500);
  };

  return (
    <div className="flex min-h-screen flex-col px-4 py-8">
      <div className="mx-auto w-full max-w-3xl flex-1">
        <Link
          href="/"
          className="mb-8 inline-flex items-center gap-2 text-sm text-sacred-text-muted transition-colors hover:text-gold"
        >
          <ArrowLeft className="h-4 w-4" />
          Powrót
        </Link>

        <div className="mb-6 text-center">
          <h1 className="font-heading mb-3 text-3xl text-gold">
            Kierownik Duchowy AI
          </h1>
          <p className="text-sacred-text-muted">
            Rozmowa w duchu wybranej tradycji duchowej
          </p>
        </div>

        {/* Disclaimer */}
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-sacred-red/20 bg-sacred-red/5 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-sacred-red-light" />
          <p className="text-sm leading-relaxed text-sacred-text-muted">
            <strong className="text-parchment">Uwaga:</strong> AI nie zastępuje
            ludzkiego kierownika duchowego. To narzędzie ma charakter pomocniczy
            i edukacyjny. W poważnych kwestiach duchowych, zwróć się do kapłana
            lub doświadczonego kierownika duchowego.
          </p>
        </div>

        {/* Tradition selector */}
        <div className="mb-6 grid grid-cols-2 gap-2 md:grid-cols-4">
          {TRADITIONS.map((t) => (
            <button
              key={t.key}
              onClick={() => setSelectedTradition(t.key)}
              className={`rounded-lg border p-3 text-left transition-all ${
                selectedTradition === t.key
                  ? "border-gold/40 bg-gold/10 text-gold"
                  : "border-sacred-border bg-sacred-surface text-sacred-text-muted hover:border-gold/20"
              }`}
            >
              <p className="text-sm font-semibold">{t.label}</p>
              <p className="mt-1 hidden text-xs opacity-70 md:block">
                {t.description}
              </p>
            </button>
          ))}
        </div>

        {/* Chat area */}
        <div className="flex min-h-[400px] flex-col rounded-xl border border-sacred-border bg-sacred-surface">
          {/* Messages */}
          <div className="flex-1 space-y-4 overflow-y-auto p-4 md:p-6">
            {messages.length === 0 && (
              <div className="py-16 text-center">
                <p className="font-scripture text-sacred-text-muted/50">
                  Rozpocznij rozmowę. Podziel się tym, co leży Ci na sercu.
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-xl px-4 py-3 ${
                    msg.role === "user"
                      ? "bg-gold/10 text-parchment"
                      : "border border-sacred-border bg-sacred-surface-light text-sacred-text"
                  }`}
                >
                  {msg.role === "director" && (
                    <p className="mb-1 text-xs font-semibold text-gold">
                      Kierownik Duchowy
                    </p>
                  )}
                  <p className="leading-relaxed">{msg.content}</p>
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex justify-start">
                <div className="rounded-xl border border-sacred-border bg-sacred-surface-light px-4 py-3">
                  <p className="text-xs font-semibold text-gold">
                    Kierownik Duchowy
                  </p>
                  <div className="mt-2 flex gap-1">
                    <span className="animate-sacred-pulse h-2 w-2 rounded-full bg-gold/50" />
                    <span className="animate-sacred-pulse h-2 w-2 rounded-full bg-gold/50 [animation-delay:0.5s]" />
                    <span className="animate-sacred-pulse h-2 w-2 rounded-full bg-gold/50 [animation-delay:1s]" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <form
            onSubmit={handleSend}
            className="border-t border-sacred-border p-4"
          >
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Napisz swoją myśl lub pytanie..."
                className="flex-1 rounded-lg border border-sacred-border bg-sacred-bg px-4 py-3 text-sacred-text placeholder-sacred-text-muted/50 transition-colors focus:border-gold/50 focus:outline-none"
                disabled={isTyping}
              />
              <button
                type="submit"
                disabled={!input.trim() || isTyping}
                className="flex items-center gap-2 rounded-lg border border-gold/40 bg-gold/10 px-5 py-3 text-gold transition-all hover:bg-gold/20 disabled:cursor-not-allowed disabled:opacity-30"
              >
                <Send className="h-4 w-4" />
                <span className="hidden sm:inline">Wyślij</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
