import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        critical: "#dc2626",
        high: "#f59e0b",
        medium: "#fbbf24",
        low: "#10b981",
      },
    },
  },
  plugins: [],
} satisfies Config;
