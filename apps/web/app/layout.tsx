import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: { default: "SwipeHire — India's AI Job Platform", template: "%s | SwipeHire" },
  description: "Swipe right on your dream job. AI-powered job matching for India.",
  keywords: ["jobs", "india", "job search", "fresher jobs", "IT jobs", "ai matching"],
  manifest: "/manifest.json",
  icons: { icon: "/favicon.ico" },
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: "https://swipehire.in",
    siteName: "SwipeHire",
  },
};

export const viewport: Viewport = {
  themeColor: "#16a34a",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
