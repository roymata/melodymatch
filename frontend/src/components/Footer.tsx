export default function Footer() {
  return (
    <footer className="mt-auto border-t border-gray-800/50 py-6">
      <div className="max-w-3xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-gray-600">
        <div className="flex flex-col sm:flex-row items-center gap-1 sm:gap-2">
          <span className="font-medium text-gray-500">MelodyMatch</span>
          <span className="hidden sm:inline text-gray-700">|</span>
          <span>Built with librosa, React & too many late-night Spotify sessions</span>
        </div>
        <div className="flex gap-4">
          <a
            href="https://github.com/roymata/melodymatch"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-gray-400 transition-colors"
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
