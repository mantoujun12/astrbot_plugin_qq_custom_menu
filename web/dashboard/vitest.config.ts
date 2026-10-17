import { mergeConfig } from 'vite'
import { defineConfig } from 'vitest/config'
import viteConfig from './vite.config.ts'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'happy-dom',
      include: ['src/**/*.test.ts'],
      setupFiles: ['./src/test/setup.ts'],
      server: {
        deps: {
          inline: [/vuetify/],
        },
      },
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov'],
        include: ['src/**/*.{ts,vue}'],
        exclude: ['src/**/*.test.ts', 'src/main.ts', 'src/test/**'],
        // 阈值按实测值往下留 3-5 个百分点，既给跨环境浮动留余量，
        // 也能拦住覆盖率明显回落。
        thresholds: {
          lines: 85,
          statements: 85,
          functions: 80,
          branches: 80,
        },
      },
    },
  }),
)
