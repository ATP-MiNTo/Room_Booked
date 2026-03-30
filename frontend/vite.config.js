import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true,
    // เพิ่มการตั้งค่า Proxy ตรงนี้
    proxy: {
      '/data': 'http://localhost:8000',
      '/reservations': 'http://localhost:8000',
      '/booked-seats': 'http://localhost:8000',
      '/reserve-with-image': 'http://localhost:8000'
    }
  }
})