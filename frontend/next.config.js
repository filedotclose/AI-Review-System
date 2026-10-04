const isWebpack = process.argv.includes('--webpack');
const isTurbopack =
  !isWebpack &&
  (process.env.TURBOPACK === '1' ||
    process.argv.includes('--turbopack') ||
    process.argv.includes('--turbo') ||
    true); // Turbopack is enabled by default in Next.js 16

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  turbopack: {},
};

let config = nextConfig;

if (!isTurbopack) {
  try {
    const withPWA = require("@ducanh2912/next-pwa").default({
      dest: "public",
      disable: process.env.NODE_ENV === "development",
      register: true,
      skipWaiting: true,
    });
    config = withPWA(nextConfig);
  } catch (e) {
    // If PWA plugin is incompatible with the bundler or environment, proceed with base configuration
    console.warn("PWA build plugin disabled or not supported in current environment");
  }
}

module.exports = config;
