/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans:    ['"Inter"', 'sans-serif'],
        display: ['"Playfair Display"', 'serif'],
        mono:    ['"DM Mono"', 'monospace'],
      },
      colors: {
        // ARCX brand palette matching Apple-inspired luxury
        arcx: {
          gold:  '#E1C389', // Rich, elegant gold
          green: '#30D158', // iOS green
          red:   '#FF453A', // iOS red
          blue:  '#0A84FF', // iOS blue
        },
        vault: {
          DEFAULT: '#000000', // Pure OLED black
          card:    '#111111', // Very dark surface
          border:  'rgba(255, 255, 255, 0.08)', // Apple-style subtle glass border
        },
        text: {
          primary: '#F5F5F7', // Apple primary text
          secondary: '#86868B', // Apple secondary text
          muted: '#6E6E73',
        }
      },
      animation: {
        'fade-in':      'fadeIn .35s ease forwards',
        'slide-up':     'slideUp .4s ease forwards',
        'pulse-green':  'pulseGreen 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn:     { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp:    { from: { opacity: 0, transform: 'translateY(12px)' }, to: { opacity: 1, transform: 'none' } },
        pulseGreen: { '0%,100%': { boxShadow: '0 0 0 0 rgba(16,185,129,.4)' }, '50%': { boxShadow: '0 0 0 8px rgba(16,185,129,0)' } },
      },
    },
  },
  plugins: [],
}