import type { Metadata, Viewport } from "next";
import { Bricolage_Grotesque, DM_Sans } from "next/font/google";
import Link from "next/link";

import { siteUrl } from "@/lib/seo";

import "./globals.css";

const display = Bricolage_Grotesque({
  subsets: ["latin"],
  weight: ["800"],
  variable: "--font-display",
});
const text = DM_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-text",
});

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl()),
  title: {
    default: "Garimpei: preço de livro novo e usado",
    template: "%s · Garimpei",
  },
  description:
    "Compare o preço de livros novos e usados nas livrarias e sebos do Brasil e veja quanto dá para economizar.",
};

export const viewport: Viewport = { themeColor: "#ffc928" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${display.variable} ${text.variable}`}>
      <body>
        {children}
        <footer className="footer">
          <div className="container muted">
            <p>
              Preços coletados uma vez por dia nas lojas. Confira o valor final na loja
              antes de comprar.
            </p>
            <p>
              <Link href="/">Garimpei</Link>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
