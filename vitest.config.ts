import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    globals: true,
    environment: 'node',
    passWithNoTests: true,
    include: ['src/__tests__/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      include: ['src/lib/**', 'src/app/**'],
      exclude: ['src/__tests__/**'],
    },
  },
});
