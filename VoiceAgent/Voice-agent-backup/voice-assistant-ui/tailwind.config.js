/** @type {import('tailwindcss').Config} */

import { nextui } from "@nextui-org/react";

export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./node_modules/@nextui-org/theme/dist/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'mbta-blue': '#0D2D83',
        'mbta-orange': '#CE8B2D',
        'mbta-red': '#C02D1D',
        'mbta-green': '#367437',
      },
      backgroundImage: {
        'mbta-lines': 'linear-gradient(to bottom, #0D2D83, #CE8B2D, #C02D1D, #367437)',
        'mbta-background': "url('../public/mbta-background.png')",
      },
    },
  },
  darkMode: "class",
  plugins: [nextui()],
}; 