/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // We can toggle this by adding 'dark' class to html
  theme: {
    extend: {
      colors: {
        primary: "var(--primary)",
        secondary: "var(--secondary)",
        surface: "var(--surface)",
        text: "var(--text)",
        error: "var(--error)",
        background: "var(--background)"
      },
      fontFamily: {
        space: ['"Space Grotesk"', "sans-serif"],
      },
      keyframes: {
        streamDown: {
          '0%': { top: '0%', opacity: '0' },
          '5%': { opacity: '1' },
          '95%': { opacity: '1' },
          '100%': { top: '100%', opacity: '0' },
        },
        streamLeft: {
          '0%': { right: '0%', opacity: '0' },
          '5%': { opacity: '1' },
          '95%': { opacity: '1' },
          '100%': { right: '100%', opacity: '0' },
        },
        streamRight: {
          '0%': { left: '0%', opacity: '0' },
          '5%': { opacity: '1' },
          '95%': { opacity: '1' },
          '100%': { left: '100%', opacity: '0' },
        }
      },
      animation: {
        streamDown: 'streamDown 2s linear infinite',
        streamLeft: 'streamLeft 2s linear infinite',
        streamRight: 'streamRight 2s linear infinite'
      }
    },
  },
  plugins: [],
}
