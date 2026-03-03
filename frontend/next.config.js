/** @type {import('next').NextConfig} */
const nextConfig = {
  images: { unoptimized: true },

  async rewrites() {
    const backend =
      process.env.BACKEND_URL ||
      'https://cert-navigator-production.up.railway.app';
    return [
      {
        source: '/backend/:path*',
        destination: `${backend}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
