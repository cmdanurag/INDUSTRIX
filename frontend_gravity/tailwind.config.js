/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: '#111417',
        'surface-low': '#191c1f',
        'surface-container': '#1d2023',
        'surface-high': '#282a2e',
        'surface-highest': '#323539',
        'surface-bright': '#37393d',
        primary: '#dab9ff',
        'primary-container': '#b072fb',
        'on-surface': '#e1e2e7',
        'on-surface-variant': '#cec2d5',
        outline: '#978d9e',
        'outline-variant': '#4b4453',
        tertiary: '#efc050',
        error: '#ffb4ab',
        'error-container': '#93000a',
      },
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['Inter', 'monospace'],
      },
    },
  },
  plugins: [],
}
