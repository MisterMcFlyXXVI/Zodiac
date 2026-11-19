import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "zbot · Zodiac cipher hypothesis tester",
  description: "Results of an automated, statistically honest search of the unsolved Zodiac ciphers Z13 and Z32.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="topbar">
          <div className="topbar-inner">
            <a href="/" className="brand">
              zbot <span>· Zodiac Z13 &amp; Z32</span>
            </a>
            <Nav />
          </div>
        </header>
        <main className="page">
          {children}
          <footer className="footer">
            zbot tests hypotheses about the unsolved Zodiac ciphers and reports how much each result can be trusted.
            It does not identify anyone. Data from the bot&apos;s public ledger on GitHub; refreshes every couple of minutes.
          </footer>
        </main>
      </body>
    </html>
  );
}
