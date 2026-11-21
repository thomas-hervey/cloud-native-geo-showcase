'use client'

import { useAuth } from '@/contexts/AuthContext'

export function SignOutButton() {
  const { signOut } = useAuth()
  return (
    <button
      onClick={() => signOut()}
      className="bg-white text-blue-700 hover:bg-blue-50 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
    >
      Sign Out
    </button>
  )
}
