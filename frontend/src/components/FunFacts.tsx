const FACTS = [
  {
    emoji: "🎵",
    title: "4 Chords, Infinite Hits",
    text: "Most pop hits use the same I-V-vi-IV chord progression. That's why your brain thinks every radio song sounds familiar.",
  },
  {
    emoji: "🥁",
    title: "The 120 BPM Sweet Spot",
    text: "The most popular tempo in music history is ~120 BPM — the natural pace of walking. Coincidence? Your feet don't think so.",
  },
  {
    emoji: "🧬",
    title: "Audio DNA Is Real",
    text: "Every song has a unique fingerprint made of MFCCs, chroma vectors, and spectral contrast. We compare those to measure similarity.",
  },
];

export default function FunFacts() {
  return (
    <section className="mt-16 mb-8">
      <h2 className="text-center text-sm font-semibold text-gray-500 uppercase tracking-wider mb-6">
        Did you know?
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {FACTS.map((fact, i) => (
          <div
            key={i}
            className="rounded-xl bg-gray-800/40 border border-gray-800 p-5 text-center"
          >
            <span className="text-2xl">{fact.emoji}</span>
            <h3 className="mt-2 text-sm font-semibold text-gray-200">{fact.title}</h3>
            <p className="mt-1.5 text-xs text-gray-500 leading-relaxed">{fact.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
