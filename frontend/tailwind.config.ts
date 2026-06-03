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
          700: "#10313f"
        },
        grass: {
          500: "#1db954",
          400: "#39d27d"
        },
        gold: "#f5c451"
      },
      boxShadow: {
        card: "0 18px 50px rgba(0, 0, 0, 0.28)"
      }
    }
  },
  plugins: []
};

export default config;
