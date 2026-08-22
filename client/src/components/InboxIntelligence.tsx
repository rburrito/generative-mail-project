import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Drawer,
  DrawerTrigger,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import { Sparkles, Loader2 } from "lucide-react"
import type { Email } from "@/types"
import { ai } from "@/ai"

/** Global, inbox-wide AI: no-arg reports (digest/commitments/analytics), a free
 * text Ask, and topic clustering for a chosen sender. */
export function InboxIntelligence({ emails }: { emails: Email[] }) {
  const [loadingLabel, setLoadingLabel] = useState<string | null>(null)
  const [resultLabel, setResultLabel] = useState("")
  const [output, setOutput] = useState("")
  const [question, setQuestion] = useState("")
  const [sender, setSender] = useState("")

  const senders = Array.from(new Set(emails.map((e) => e.sender))).sort()
  const busy = loadingLabel !== null

  const run = async (label: string, fn: () => Promise<string>) => {
    setLoadingLabel(label)
    setOutput("")
    try {
      setResultLabel(label)
      setOutput(await fn())
    } catch (e) {
      setResultLabel(label)
      setOutput(`Error: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setLoadingLabel(null)
    }
  }

  return (
    <Drawer direction="right">
      <DrawerTrigger asChild>
        <Button variant="outline" size="sm">
          <Sparkles className="size-4" /> Intelligence
        </Button>
      </DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>Inbox Intelligence</DrawerTitle>
        </DrawerHeader>

        <div className="flex flex-col gap-3 px-4 pb-3">
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" disabled={busy} onClick={() => run("Digest", ai.digest)}>
              Digest
            </Button>
            <Button variant="outline" size="sm" disabled={busy} onClick={() => run("Commitments", ai.commitments)}>
              Commitments
            </Button>
            <Button variant="outline" size="sm" disabled={busy} onClick={() => run("Analytics", ai.analytics)}>
              Analytics
            </Button>
          </div>

          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              if (question.trim()) run("Ask", () => ai.ask(question))
            }}
          >
            <Input
              placeholder="Ask about your inbox…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
            <Button type="submit" size="sm" disabled={busy || !question.trim()}>
              Ask
            </Button>
          </form>

          <div className="flex gap-2">
            <select
              className="flex-1 h-9 rounded-md border border-input bg-transparent px-3 text-sm"
              value={sender}
              onChange={(e) => setSender(e.target.value)}
            >
              <option value="">Cluster a sender's mail…</option>
              {senders.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <Button size="sm" variant="outline" disabled={busy || !sender} onClick={() => run("Clusters", () => ai.clusters(sender))}>
              Cluster
            </Button>
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-4">
          {loadingLabel ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> Running {loadingLabel}…
            </div>
          ) : output ? (
            <>
              <div className="text-xs font-medium text-muted-foreground mb-2">{resultLabel}</div>
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">{output}</pre>
            </>
          ) : (
            <div className="text-sm text-muted-foreground">
              Run a report, ask a question, or cluster a sender's mail.
            </div>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  )
}
