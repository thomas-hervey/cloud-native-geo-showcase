import Link from "next/link";

export default function AuthErrorPage() {
  const loginUrl = "/login";

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center max-w-md mx-auto p-8">
        <div className="text-red-500 mb-4">
          <svg
            className="w-16 h-16 mx-auto"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-gray-900 mb-3">
          Authentication Error
        </h1>
        <p className="text-gray-600 mb-6">
          We weren&apos;t able to verify your session. This can happen if your
          session expired or there was an issue with the login flow.
        </p>
        <div className="space-y-3">
          <a
            href={loginUrl}
            className="block w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Try signing in again
          </a>
          <Link
            href="/cng-modules"
            className="block w-full px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
          >
            Browse CNG Modules (no sign-in required)
          </Link>
        </div>
      </div>
    </div>
  );
}
