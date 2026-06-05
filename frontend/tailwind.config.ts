import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        pitch: {
          900: "#07181f",
          800: "#0b222d",
          700: "#10313f",
          650: "#143847"
        },
        surface: {
          hero: "rgba(18, 43, 55, 0.72)",
          card: "rgba(255, 255, 255, 0.055)",
          inset: "rgba(2, 12, 18, 0.42)"
        },
        grass: {
          500: "#1db954",
          400: "#39d27d"
        },
        gold: "#f5c451",
        source: {
          statsbomb: "#69b7ff",
          fbref: "#39d27d",
          understat: "#f5c451"
        }
      },
      boxShadow: {
        card: "0 18px 50px rgba(0, 0, 0, 0.28)",
        premium: "0 24px 80px rgba(0, 0, 0, 0.36)"
      }
    }
  },
  plugins: []
};

export default config;
