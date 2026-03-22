import type { Metadata } from "next";
import "./globals.css";
import QueryProvider from "@/components/ui/QueryProvider";

export const metadata: Metadata = {
  title: "Nano Atoms - AI App Generator",
  description:
    "Describe an app in natural language and generate an interactive result with multiple AI agents.",
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
