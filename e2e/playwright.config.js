const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: '.',
  testMatch: '**/*.spec.js',
  timeout: 90000,
  expect: { timeout: 15000 },
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.EMAIL_GAMES_BASE_URL || 'http://127.0.0.1:18080',
    headless: true,
    trace: 'retain-on-failure'
  }
});