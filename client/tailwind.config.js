/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"Courier New"', "monospace"],
        orbitron: ["Orbitron", "sans-serif"],
      },
    },
  },
  plugins: [],
};
