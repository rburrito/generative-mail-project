export const PRIMARY_USER = "pm@acme.com"
export const API_BASE = "http://localhost:5000"

// Optional API key for the protected /ai/* and /reset routes. Set VITE_API_KEY
// in the client env to match the server's APP_API_KEY. Empty in dev (auth off).
export const API_KEY = (import.meta.env as Record<string, string | undefined>).VITE_API_KEY

export function authHeaders(): Record<string, string> {
  return API_KEY ? { "X-API-Key": API_KEY } : {}
}
