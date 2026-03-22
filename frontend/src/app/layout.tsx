import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'SignAI_OS — AI-Powered Sign Language Communication System',
  description:
    'Real-time sign language to speech and speech to sign language translation powered by edge AI. Designed for universal accessibility.',
  keywords: [
    'sign language',
    'AI',
    'accessibility',
    'MediaPipe',
    'TensorFlow',
    'real-time translation',
    'speech to sign',
    'sign to speech',
  ],
  authors: [{ name: 'SignAI Team' }],
  openGraph: {
    title: 'SignAI_OS — AI Communication System',
    description: 'Break communication barriers with real-time AI-powered sign language translation.',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[#050505] text-[#e0e0e0] overflow-x-hidden">
        {children}
      </body>
    </html>
  );
}
