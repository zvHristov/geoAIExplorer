/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["mapbox-gl", "@mapbox/mapbox-gl-draw"],
};

module.exports = nextConfig;
