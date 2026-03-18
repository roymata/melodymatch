export default function Footer() {
  return (
    <footer className="mt-auto border-t border-gray-800/50 py-6">
      <div className="max-w-3xl mx-auto px-4 flex items-center justify-between text-xs text-gray-600">
        <span>SongDiff</span>
        <div className="flex gap-4">
          <span>About</span>
          <span>Privacy</span>
          <a
            href="https://github.com"
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
