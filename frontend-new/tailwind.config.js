/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#111417",
        "surface-low": "#191c1f",
        "surface-container": "#1d2023",
        "surface-high": "#282a2e",
        "surface-highest": "#323539",
        primary: "#dab9ff",
        "primary-container": "#b072fb",
        "on-surface": "#e1e2e7",
        "on-surface-variant": "#cec2d5",
        tertiary: "#efc050",
        error: "#ffb4ab"
      }
    }
  },
  plugins: []
};
