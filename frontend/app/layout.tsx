import type { Metadata } from "next";
import "./globals.css";
import "@xyflow/react/dist/style.css";
import "@xterm/xterm/css/xterm.css";

export const metadata: Metadata = {
  title: "ROS 2 Academy",
  description: "Interactive ROS 2 Jazzy robotics programming laboratory",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
