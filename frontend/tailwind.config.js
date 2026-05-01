/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ford: {
          blue: "#003478",
          accent: "#1c69d4",
          ink: "#0a0e14",
          ash: "#3b4453",
          mist: "#eef2f8",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      boxShadow: {
        soft: "0 4px 24px rgba(2, 12, 40, 0.08)",
      },
    },
  },
  plugins: [],
};
