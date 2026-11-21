import { FC, ReactNode } from 'react';
import Link from 'next/link';

interface LayoutProps {
  children: ReactNode;
}

const Layout: FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-blue-700 text-white shadow-md">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-col md:flex-row md:justify-between md:items-center">
            <Link href="/" className="text-2xl font-bold">
              Thomas&apos; Role and Technology Learning Hub
            </Link>
            <nav className="mt-4 md:mt-0">
              <ul className="flex space-x-6">
                <li>
                  <Link
                    href="/"
                    className="hover:text-blue-200 transition-colors"
                  >
                    Home
                  </Link>
                </li>
                <li>
                  <Link
                    href="/modules"
                    className="hover:text-blue-200 transition-colors"
                  >
                    Modules
                  </Link>
                </li>
                <li>
                  <a
                    href="https://conference.cloudnativegeo.org/CNGConference2025"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-blue-200 transition-colors"
                  >
                    CNG Conference
                  </a>
                </li>
              </ul>
            </nav>
          </div>
        </div>
      </header>
      <main className="container mx-auto px-4 py-8">
        {children}
      </main>
    </div>
  );
};

export default Layout;
