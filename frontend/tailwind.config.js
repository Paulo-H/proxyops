/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts,js}'],
  theme: {
    extend: {
      colors: {
        // Brand palette derived from the ProxyOps logo: deep navy + electric blues.
        brand: {
          50:  '#eef4ff',
          100: '#d9e6ff',
          200: '#b5cdff',
          300: '#85a8ff',
          400: '#5b86ff',
          500: '#2c6cff',  // accent
          600: '#1f4fd9',
          700: '#1a3da3',
          800: '#152e7a',
          900: '#0d1f57',
          950: '#070f33',
        },
        ink: {
          50:  '#f6f8fb',
          100: '#e9edf5',
          200: '#cdd5e3',
          300: '#9ba8c4',
          400: '#6a7a9d',
          500: '#475877',
          600: '#33415a',
          700: '#222d44',
          800: '#161e2e',
          900: '#0c121f',
          950: '#060912',
        },
      },
      fontFamily: {
        sans: ['"Inter"', '"Segoe UI"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(13, 31, 87, .06), 0 8px 24px -8px rgba(13, 31, 87, .12)',
        glow: '0 0 0 4px rgba(44, 108, 255, 0.18)',
      },
    },
  },
  plugins: [],
};
