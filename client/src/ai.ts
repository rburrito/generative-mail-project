// Client for the server's AI endpoints. Most return formatted text/plain, so we
// fetch text and render it as-is; classify/ask return JSON, which we shape here.
import { API_BASE, authHeaders } from "@/constants"

async function getText(path: string): Promise<string> {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`Request failed (${res.status})`)
  return (await res.text()).trim()
}

async function getJson<T = any>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`Request failed (${res.status})`)
  return res.json()
}

export type Draft = {
  reply_to_name: string
  topic: string
  subject: string
  body: string
}

export const ai = {
  // Thread-scoped
  summarize: (threadId: string) => getText(`/ai/summarize/${threadId}`),
  state: (threadId: string) => getText(`/ai/state/${threadId}`),
  urgency: (threadId: string) =>
    getText(`/ai/urgency?thread_id=${encodeURIComponent(threadId)}`),
  classify: async (threadId: string) => {
    const d = await getJson(`/ai/classify/${threadId}`)
    return `Urgency: ${d.urgency}\nState: ${d.thread_state}\nCategory: ${d.category}\n\n${d.reason}`
  },
  draft: (threadId: string) =>
    getJson<Draft>(`/ai/draft?thread_id=${encodeURIComponent(threadId)}&format=json`),

  // Global
  digest: () => getText(`/ai/digest`),
  commitments: () => getText(`/ai/commitments`),
  analytics: () => getText(`/analytics`),
  clusters: (sender: string) =>
    getText(`/ai/clusters?sender=${encodeURIComponent(sender)}`),
  ask: async (question: string) => {
    const res = await fetch(`${API_BASE}/ai/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ question }),
    })
    if (!res.ok) throw new Error(`Request failed (${res.status})`)
    return (await res.json()).answer as string
  },
}
