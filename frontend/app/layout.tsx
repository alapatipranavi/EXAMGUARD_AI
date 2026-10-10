import type { Metadata } from "next";
import "./globals.css";
import { MediaPipeConsoleFilter } from "@/components/MediaPipeConsoleFilter";

export const metadata: Metadata = {
  title: "ExamGuard AI — Intelligent Examination and Integrity Assessment System",
  description: "AI-powered secure online examination, automated proctoring, and adaptive integrity assessment platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased selection:bg-blue-600 selection:text-white">
        <MediaPipeConsoleFilter />
        {children}
      </body>
    </html>
  );
}
