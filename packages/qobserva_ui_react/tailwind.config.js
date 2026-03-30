/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#0f172a',
          surface: '#1e293b',
          border: '#334155',
          text: '#e2e8f0',
          'text-muted': '#94a3b8',
        },
        primary: {
          DEFAULT: '#3b82f6',
          dark: '#2563eb',
          light: '#60a5fa',
        },
        success: '#10b981',
        warning: '#f59e0b',
        error: '#ef4444',
      },
    },
  },
  plugins: [],
}
