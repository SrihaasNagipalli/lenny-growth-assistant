/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        lenny: {
          50:  '#f0f4ff',
          100: '#e0eaff',
          200: '#c7d6ff',
          500: '#4361ee',
          600: '#3451d1',
          700: '#2a3fb5',
          900: '#1a2456',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
