/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#0F2A4A", light: "#1B3E66", dark: "#081A2E" },
        gold: { DEFAULT: "#C8A96A", light: "#DBC08A", dark: "#9C7F42" },
        cream: { DEFAULT: "#F7F5F0", dark: "#EDE9E0" },
        slateDalil: { DEFAULT: "#2A2F3A", light: "#4A5162" },
        success: "#2F855A",
        warning: "#D69E2E",
        danger: "#C53030",
      },
    },
  },
  plugins: [],
};