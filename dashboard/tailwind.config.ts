import type { Config } from "tailwindcss";

/**
 * Amaya brand palette — rating-grade coding aside, the UI leans on a
 * calm graphite + accent-copper scheme so numbers pop without screaming.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "Menlo", "monospace"],
      },
      colors: {
        ink: {
          950: "#0a0b0f",
          900: "#101218",
          850: "#171a22",
          800: "#1e222c",
          700: "#2b3140",
          600: "#3d4454",
          500: "#5a6375",
          400: "#8a93a6",
          300: "#b8c0d0",
          200: "#d8dde8",
          100: "#eff1f7",
        },
        copper: {
          500: "#c26b3c",
          400: "#d6875a",
          300: "#e6a483",
        },
        grade: {
          aplus: "#1fbd8a",
          a: "#31c29a",
          bplus: "#7dbb59",
          b: "#b6b042",
          cplus: "#d49636",
          c: "#d97140",
          d: "#c84b3d",
          f: "#9d2f25",
        },
      },
      boxShadow: {
        card: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 6px 24px -12px rgba(0,0,0,0.45)",
        glow: "0 0 0 1px rgba(194,107,60,0.35), 0 0 24px -4px rgba(194,107,60,0.35)",
      },
      animation: {
        pulse_ring: "pulse_ring 1.6s ease-in-out infinite",
      },
      keyframes: {
        pulse_ring: {
          "0%, 100%": { opacity: "0.4", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.02)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
