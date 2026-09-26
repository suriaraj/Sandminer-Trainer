import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PYRO RENTALS | Vehicle rentals made clear",
  description: "Self-drive, chauffeur, airport and outstation vehicle rentals."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
