import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import svgr from 'vite-plugin-svgr';
// https://vite.dev/config/
export default defineConfig({
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
    theme: {
      extend: {
        colors: {
          'bg-color': '#151C1F',
          'blue-start': '#1E5BB2',
          'blue-end': '#5CBDE9',
        },
        fontFamily: {
          urbanist: ['Urbanist', 'sans-serif'],
        },
      },
    },
  plugins: [react(),tailwindcss(),svgr()],
})
