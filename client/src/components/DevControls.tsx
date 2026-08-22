import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Drawer,
  DrawerTrigger,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerFooter,
  DrawerClose,
} from "@/components/ui/drawer"
import type { Email } from "@/types"
import { PRIMARY_USER, API_BASE } from "@/constants"

interface DevControlsProps {
  onReset: () => void
  emails: Email[]
  onEmailCreated: () => void
}

const CONTACTS = [
  "david.park@acme.com",
  "jennifer.walsh@acme.com",
  "lisa.thompson@acme.com",
  "marcus.rivera@acme.com",
  "mike.johnson@acme.com",
  "rachel.kim@acme.com",
  "sarah.chen@acme.com",
]

export function DevControls({ onReset, emails, onEmailCreated }: DevControlsProps) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [sender, setSender] = useState(CONTACTS[0])
  const [threadId, setThreadId] = useState("")
  const [subject, setSubject] = useState("")
  const [body, setBody] = useState("")

  const threads = Array.from(
    new Map(emails.map((e) => [e.thread_id, { id: e.thread_id, subject: e.subject }])).values()
  )

  const handleCreate = () => {
    fetch(`${API_BASE}/emails`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sender,
        recipient: PRIMARY_USER,
        subject,
        body,
        ...(threadId && { thread_id: threadId }),
      }),
    }).then(() => {
      setSender(CONTACTS[0])
      setThreadId("")
      setSubject("")
      setBody("")
      setDrawerOpen(false)
      onEmailCreated()
    })
  }

  return (
    <div className="flex items-center justify-end gap-2 px-4 py-2 border-b bg-destructive/50">
      <span className="text-xs font-medium text-destructive-foreground">Dev Controls:</span>
      <Button variant="outline" size="xs" onClick={onReset}>
        Reset DB
      </Button>
      <Drawer direction="right" open={drawerOpen} onOpenChange={setDrawerOpen}>
        <DrawerTrigger asChild>
          <Button variant="outline" size="xs">
            Mock Email
          </Button>
        </DrawerTrigger>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>Create Mock Incoming Email</DrawerTitle>
          </DrawerHeader>
          <div className="flex flex-col gap-4 p-4">
            <div>
              <label className="text-sm font-medium mb-1.5 block">From</label>
              <select
                className="w-full h-9 rounded-md border border-input bg-transparent px-3 text-sm"
                value={sender}
                onChange={(e) => setSender(e.target.value)}
              >
                {CONTACTS.map((contact) => (
                  <option key={contact} value={contact}>
                    {contact}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Thread</label>
              <select
                className="w-full h-9 rounded-md border border-input bg-transparent px-3 text-sm"
                value={threadId}
                onChange={(e) => setThreadId(e.target.value)}
              >
                <option value="">New Thread</option>
                {threads.map((thread) => (
                  <option key={thread.id} value={thread.id}>
                    {thread.subject} ({thread.id.slice(0, 8)})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Subject</label>
              <Input
                placeholder="Email subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">Body</label>
              <Textarea
                placeholder="Email body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="min-h-32"
              />
            </div>
          </div>
          <DrawerFooter>
            <Button onClick={handleCreate}>Create</Button>
            <DrawerClose asChild>
              <Button variant="outline">Cancel</Button>
            </DrawerClose>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>
    </div>
  )
}
