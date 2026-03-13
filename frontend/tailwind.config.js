/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          bg:      "#0a0a12",
          surface: "#11111f",
          card:    "#16162a",
          border:  "#2a2a45",
          purple:  "#a855f7",
          pink:    "#ec4899",
          glow:    "#7c3aed",
        }
      },
      fontFamily: {
        display: ["'Rajdhani'", "sans-serif"],
        body:    ["'DM Sans'", "sans-serif"],
        mono:    ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        glow:       "0 0 20px rgba(168,85,247,0.35)",
        "glow-sm":  "0 0 10px rgba(168,85,247,0.25)",
        "glow-pink":"0 0 20px rgba(236,72,153,0.35)",
      },
      keyframes: {
        flicker: {
          "0%,100%": { opacity: "1" },
          "92%":     { opacity: "1" },
          "93%":     { opacity: "0.6" },
          "94%":     { opacity: "1" },
          "96%":     { opacity: "0.8" },
          "97%":     { opacity: "1" },
        },
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4,0,0.6,1) infinite",
        "flicker":    "flicker 4s ease-in-out infinite",
      }
    }
  },
  plugins: []
}