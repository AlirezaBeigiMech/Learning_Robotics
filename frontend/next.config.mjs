const isDev = process.env.NODE_ENV === "development";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export", // static files served by the FastAPI backend
  images: { unoptimized: true },
  reactStrictMode: false,
  // During `npm run dev` (port 3000) forward REST calls to the backend; WebSockets connect to :8000 directly.
  ...(isDev && {
    async rewrites() {
      return [{ source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" }];
    },
  }),
};
export default nextConfig;
