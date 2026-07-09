import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Task Management App',
  description: 'Simple task management app',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
