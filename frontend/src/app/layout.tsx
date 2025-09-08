import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Financial Analytics Dashboard",
  description: "Analyze commitment amounts, deals, and outstanding amounts with advanced filtering",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <nav className="bg-white/90 backdrop-blur-sm border-b border-slate-200/50 sticky top-0 z-50">
          <div className="container mx-auto px-6 py-3">
            <div className="flex items-center justify-between">
              <Link href="/" className="flex items-center gap-2 font-semibold text-slate-900">
                📊 Financial Analytics
              </Link>
              <div className="flex items-center gap-4">
                <Link href="/filters" className="text-sm text-slate-600 hover:text-slate-900 transition-colors">
                  Filters
                </Link>
                <Link href="/data" className="text-sm text-slate-600 hover:text-slate-900 transition-colors">
                  Data
                </Link>
                <Link href="/composites" className="text-sm text-slate-600 hover:text-slate-900 transition-colors">
                  Composites
                </Link>
                <Link href="/analysis" className="text-sm text-slate-600 hover:text-slate-900 transition-colors">
                  Capped Analysis
                </Link>
              </div>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
