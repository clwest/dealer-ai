/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Brand palette — dealer-agnostic slots (blue = signature cool
        // color, accent = signature warm color, plus three neutrals).
        // Post-SESSION_030 pivot values ship the Copper Canyon Auto
        // (Yuma, AZ) indie persona: softer desert-sky blue in the
        // signature slot, warm terracotta in the accent slot. Neutrals
        // unchanged — they're brand-agnostic across dealer configs.
        //
        // Franchise deployments swap values here (e.g. Dealer OS
        // used blue=#003478 and accent=#1c69d4). Consumers reference
        // brand.blue / brand.accent by role, not by literal color, so
        // a palette swap in this file recolors the whole UI without
        // touching component code.
        brand: {
          blue: "#3f6b90",
          accent: "#c76b3a",
          ink: "#0a0e14",
          ash: "#3b4453",
          mist: "#eef2f8",
        },
        // shadcn tokens — vars contain full oklch(...) expressions, so
        // we reference them directly (no hsl() wrapper).
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
        },
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
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
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
