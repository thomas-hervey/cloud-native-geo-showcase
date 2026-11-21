import { LoginForm } from '@/components/auth/LoginForm'
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? ''

function validateRedirectTo(raw: string | undefined): string {
  if (!raw) return '/'
  if (raw.startsWith('/')) return raw
  if (APP_URL && raw.startsWith(APP_URL)) return raw
  return '/'
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ redirect_to?: string }>
}) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  const { redirect_to } = await searchParams

  if (user) redirect(validateRedirectTo(redirect_to))

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <LoginForm redirectTo={validateRedirectTo(redirect_to)} />
    </div>
  )
}
