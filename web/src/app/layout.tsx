import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Civic Texas", template: "%s · Civic Texas" },
  description:
    "Follow Texas state legislation using official records. An independent, nonpartisan civic technology project.",
};

const NAV = [
  { href: "/bills", label: "Bills" },
  { href: "/methodology", label: "Methodology" },
  { href: "/about", label: "About" },
];

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col antialiased">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-2 focus:z-50 focus:bg-foreground focus:px-3 focus:py-2 focus:text-background"
        >
          Skip to content
        </a>
        <header className="border-b border-foreground">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3 sm:px-6">
            <Link href="/" className="flex items-center gap-2 font-serif text-xl font-semibold no-underline">
              <svg viewBox="0 0 24 24" className="size-4 fill-sienna" aria-hidden="true" focusable="false">
                <path d="M12 2.5l2.6 6.9 7.4.3-5.8 4.6 2 7.1L12 17.3l-6.2 4.1 2-7.1L2 9.7l7.4-.3z" />
              </svg>
              Civic Texas
            </Link>
            <nav aria-label="Main">
              <ul className="flex gap-5 text-sm font-medium">
                {NAV.map((item) => (
                  <li key={item.href}>
                    <Link href={item.href} className="hover:underline">
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
          {children}
        </main>
        <footer className="border-t border-foreground text-sm text-ink-soft">
          <div className="mx-auto max-w-5xl space-y-2 px-4 py-6 sm:px-6">
            <p>
              <strong className="text-foreground">Civic Texas is an independent civic technology project.</strong> It is
              not affiliated with the State of Texas, the Texas Legislature, any government agency or any political
              party. Nothing here is legal advice.
            </p>
            <p>
              Legislative data: Texas Legislature Online (ftp.legis.state.tx.us), Texas Legislative Council. Official
              records are the source of truth.{" "}
              <a href="https://github.com/rockysahooart/civictexas" className="underline">
                Source code
              </a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
