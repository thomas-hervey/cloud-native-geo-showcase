import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { AuthProvider } from "@/contexts/AuthContext";
import { SignOutButton } from "@/components/auth/SignOutButton";
import { createClient } from "@/lib/supabase/server";
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
  title: "Cloud-Native Geospatial Self-Learning Tutorial",
  description: "A self-paced learning journey through the fundamentals of modern web-based GIS and geospatial analysis technologies",
};

const authEnabled = process.env.NEXT_PUBLIC_FEATURE_AUTH_ENABLED !== "false";

const NAV_LINKS = [
  { href: "/scout/lab", label: "Scout", color: "bg-indigo-600 hover:bg-indigo-700", isPublic: true },
  { href: "/spatial-eval", label: "Spatial Eval", color: "bg-teal-600 hover:bg-teal-700", isPublic: true },
  { href: "/resources", label: "Resources", color: "bg-yellow-500 hover:bg-yellow-600", isPublic: false },
  { href: "/roadmap", label: "Roadmap", color: "bg-purple-500 hover:bg-purple-600", isPublic: true },
];

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Auth disabled in dev → treat as authenticated for nav purposes
  const isAuthenticated = !authEnabled || !!user;

  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-50`}
      >
        <AuthProvider>
        <header className="text-white bg-blue-700 shadow-md">
          <div className="container px-4 py-4 mx-auto">
            <div className="flex flex-col md:flex-row md:justify-between md:items-center">
              <Link href="/" className="text-2xl font-bold whitespace-nowrap">
                Cloud Native Geo Modules
              </Link>
              <nav className="mt-4 md:mt-0">
                <ul className="flex flex-wrap items-center gap-2 md:justify-end">
                  <li>
                    <Link href="/" className="hover:text-blue-200 transition-colors px-2 py-1.5 text-sm">
                      Home
                    </Link>
                  </li>
                  <li>
                    <Link
                      href="/cng-modules"
                      className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
                    >
                      CNG Modules
                    </Link>
                  </li>
                  {NAV_LINKS.map(({ href, label, color, isPublic }) => {
                    const canAccess = isAuthenticated || isPublic;
                    return canAccess ? (
                      <li key={href}>
                        <Link
                          href={href}
                          className={`${color} text-white px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap`}
                        >
                          {label}
                        </Link>
                      </li>
                    ) : (
                      <li key={href}>
                        <span
                          title="Restricted — Sign in to access"
                          className="bg-white/10 text-white/40 px-3 py-1.5 rounded-lg text-sm font-medium cursor-not-allowed select-none border border-white/10"
                        >
                          {label}
                        </span>
                      </li>
                    );
                  })}
                  {authEnabled && !user && (
                    <li>
                      <a
                        href="/login"
                        className="bg-white text-blue-700 hover:bg-blue-50 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
                      >
                        Sign In
                      </a>
                    </li>
                  )}
                  {authEnabled && user && (
                    <li>
                      <SignOutButton />
                    </li>
                  )}
                </ul>
              </nav>
            </div>
          </div>
        </header>
        <main>
          {children}
        </main>
        </AuthProvider>
      </body>
    </html>
  );
}
