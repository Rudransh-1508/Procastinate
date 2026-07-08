/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Charcoal base
        ink: {
          900: "#111111", // app background
          800: "#1c1c1c", // panels
          700: "#242424", // elevated panels
          600: "#2e2e2e", // hover / inset
          500: "#3a3a3a", // borders
        },
        fg: {
          DEFAULT: "#ededed",
          muted: "#a3a3a3",
          faint: "#707070",
        },
        // Bold coral accent
        brand: {
          DEFAULT: "#ff5a4d",
          bright: "#ff7c70",
          deep: "#e03f32",
        },
        clay: {
          DEFAULT: "#ff8a65",
          soft: "#ffab91",
        },
        ochre: {
          DEFAULT: "#f2b544",
          soft: "#f7ca75",
        },
        stone: {
          DEFAULT: "#8a97a3",
          soft: "#aab4bd",
        },
        good: "#4fb477",
        warn: "#f2b544",
        bad: "#ff5a4d",
      },
      fontFamily: {
        sans: ['"Fira Sans"', "system-ui", "sans-serif"],
        mono: ['"Fira Code"', "ui-monospace", "monospace"],
        display: ['"Fraunces"', "Georgia", "serif"],
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.02) inset, 0 10px 30px -18px rgba(0,0,0,0.7)",
      },
      borderRadius: {
        xl2: "14px",
      },
      keyframes: {
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        floaty: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        marquee: "marquee 34s linear infinite",
        floaty: "floaty 7s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
