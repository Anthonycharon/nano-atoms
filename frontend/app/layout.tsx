import type { Metadata } from "next";
import "./globals.css";
import QueryProvider from "@/components/ui/QueryProvider";

export const metadata: Metadata = {
  title: "Nano Atoms - AI App Generator",
  description:
    "Describe an app in natural language and generate an interactive result with multiple AI agents.",
  icons: {
    icon: [
      { url: "/favicon.ico?v=20260328b" },
      { url: "/icon.png?v=20260328b", type: "image/png" },
    ],
    shortcut: "/favicon.ico?v=20260328b",
    apple: "/icon.png?v=20260328b",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-stone-50 text-slate-900 antialiased">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
