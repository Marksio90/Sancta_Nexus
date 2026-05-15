export default function OfflinePage() {
  return (
    <main className="min-h-screen bg-[#0d0b1a] text-white flex flex-col items-center justify-center px-6 text-center">
      <div className="text-6xl mb-6">🕯</div>
      <h1 className="text-2xl font-bold text-[#d4af37] mb-3">Brak połączenia</h1>
      <p className="text-gray-400 max-w-sm leading-relaxed mb-8">
        Jesteś offline. Możesz jednak modlić się bez internetu —
        Bóg słyszy każde serce, niezależnie od zasięgu.
      </p>
      <div className="bg-[#d4af37]/5 border border-[#d4af37]/20 rounded-2xl p-5 max-w-sm mb-8">
        <p className="text-sm text-gray-300 italic leading-relaxed">
          «Pan jest pasterzem moim, nie brak mi niczego.
          Pozwala mi leżeć na zielonych pastwiskach.
          Prowadzi mnie nad wody, gdzie mogę odpocząć.»
        </p>
        <p className="text-xs text-gray-600 mt-2">Psalm 23,1-2</p>
      </div>
      <button
        onClick={() => window.location.reload()}
        className="bg-[#d4af37] text-black font-semibold px-8 py-3 rounded-2xl hover:bg-[#c9a227] transition-colors"
      >
        Spróbuj ponownie
      </button>
      <p className="text-xs text-gray-700 mt-6">
        Niektóre modlitwy i brewiarz są dostępne offline.
      </p>
    </main>
  );
}
