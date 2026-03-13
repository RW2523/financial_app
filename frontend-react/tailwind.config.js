/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: { DEFAULT: "#0f1116", elevated: "#161b22", muted: "#21262d" },
        accent: { DEFAULT: "#238636", hover: "#2ea043", muted: "rgba(35, 134, 54, 0.15)" },
        border: "#30363d",
        text: { primary: "#e6edf3", secondary: "#8b949e", muted: "#6e7681" },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.3)",
        glow: "0 0 0 1px rgba(35, 134, 54, 0.2)",
      },
    },
  },
  plugins: [],
};
