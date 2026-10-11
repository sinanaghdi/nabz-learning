import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "نبض یادگیری | Nabz Learning",
  description: "محیطی برای تمرین هدفمند و شناخت دقیق‌تر نقاط ضعف یادگیری",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
