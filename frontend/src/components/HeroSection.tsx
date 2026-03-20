import StatsCounter from "./StatsCounter";

const STEPS = [
  { emoji: "🔍", label: "Search two songs" },
  { emoji: "🧠", label: "AI analyzes audio DNA" },
  { emoji: "📊", label: "Get a similarity score" },
];

export default function HeroSection() {
  return (
    <header className="pt-14 pb-10 px-4">
      {/* Main headline */}
      <div className="text-center max-w-2xl mx-auto">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight bg-gradient-to-r from-brand-400 to-emerald-300 bg-clip-text text-transparent">
          MelodyMatch
        </h1>

        <p className="mt-5 text-xl md:text-2xl font-semibold text-gray-200">
          Settle the Debate Once and For All
        </p>

        <p className="mt-3 text-base text-gray-400 max-w-lg mx-auto leading-relaxed">
          Your friend swears two songs sound exactly the same.
          You think they're totally different.
          Stop arguing — let the algorithm decide.
        </p>

        {/* Counter badge */}
        <div className="mt-5">
          <StatsCounter />
        </div>
      </div>

      {/* How it works — 3 steps */}
      <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-0">
        {STEPS.map((step, i) => (
          <div key={i} className="flex items-center">
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-800/60">
              <span className="text-xl">{step.emoji}</span>
              <span className="text-sm text-gray-300">{step.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <span className="hidden sm:block text-gray-600 mx-2 text-lg">&rarr;</span>
            )}
          </div>
        ))}
      </div>
    </header>
  );
}
