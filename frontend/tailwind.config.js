/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        body: ['"Inter"', "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          50: "#f0fdf4",
          400: "#4ade80",
          500: "#22c55e",
          600: "#16a34a",
        },
        accent: {
          purple: "#a855f7",
          pink: "#ec4899",
          blue: "#3b82f6",
          cyan: "#06b6d4",
        },
      },
      boxShadow: {
        "glow-green": "0 0 20px rgba(34, 197, 94, 0.3)",
        "glow-purple": "0 0 20px rgba(168, 85, 247, 0.3)",
        "glow-pink": "0 0 20px rgba(236, 72, 153, 0.3)",
        "glow-multi":
          "0 0 30px rgba(168, 85, 247, 0.2), 0 0 60px rgba(236, 72, 153, 0.1)",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(20px) scale(0.98)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        gradientShift: {
          "0%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0% 50%" },
        },
        confettiFall: {
          "0%": {
            transform: "translateY(-10px) rotate(0deg)",
            opacity: "1",
          },
          "100%": {
            transform: "translateY(120px) rotate(720deg)",
            opacity: "0",
          },
        },
      },
      animation: {
        fadeIn: "fadeIn 0.4s ease-out",
        slideUp: "slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1)",
        float: "float 3s ease-in-out infinite",
        shimmer: "shimmer 2s linear infinite",
        "gradient-shift": "gradientShift 6s ease-in-out infinite",
        "confetti-fall": "confettiFall 1.5s ease-out forwards",
      },
    },
  },
  plugins: [],
};
