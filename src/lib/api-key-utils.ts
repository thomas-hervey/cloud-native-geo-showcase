export type ApiProvider = 'claude' | 'openai' | 'invalid'

export function detectProvider(key: string): ApiProvider {
  if (key.startsWith('sk-ant-api03-')) return 'claude'
  if (key.startsWith('sk-')) return 'openai'
  return 'invalid'
}

interface ValidationResult {
  ok: boolean
  error?: string
}

export function validateKeyForProvider(
  key: string,
  provider: 'claude' | 'openai'
): ValidationResult {
  const detected = detectProvider(key)
  if (detected === 'invalid') {
    return { ok: false, error: 'Key does not match a recognised provider prefix' }
  }
  if (detected !== provider) {
    return {
      ok: false,
      error: `Key prefix does not match requested provider: key is ${detected}, requested ${provider}`,
    }
  }
  return { ok: true }
}
