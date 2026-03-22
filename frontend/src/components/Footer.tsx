export default function Footer() {
  return (
    <footer className="mt-auto py-6 relative">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/3 h-px bg-gradient-to-r from-transparent via-accent-purple/30 to-transparent" />
      <div className="max-w-3xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-gray-600">
        <div className="flex flex-col sm:flex-row items-center gap-1 sm:gap-2">
          <span className="font-display font-medium text-gray-500">MelodyMatch</span>
          <span className="hidden sm:inline text-gray-700">|</span>
          <span>Built with React & too many late-night Spotify sessions</span>
        </div>
        <div className="flex gap-4">
          <a
            href="https://github.com/roymata/melodymatch"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-accent-purple transition-colors duration-200"
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
