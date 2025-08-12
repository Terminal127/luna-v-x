// tailwind.config.js
const { heroui } = require("@heroui/theme");

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // 1. Add your project paths back in
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",

    // 2. Include the path to ALL HeroUI components
    "./node_modules/@heroui/theme/dist/**/*.js",
  ],
  theme: {
    extend: {},
  },
  darkMode: "class",
  // 3. Make sure the heroui plugin is here
  plugins: [heroui()],
};
