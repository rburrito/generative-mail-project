import { useState, useRef, useEffect } from "react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Separator } from "@/components/ui/separator"
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
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription } from "@/components/ui/empty"
import { Reply, Trash2, Mail, Sparkles, Loader2 } from "lucide-react"
import type { Email } from "@/types"
import { PRIMARY_USER, API_BASE } from "@/constants"
import { formatDate, getInitials } from "@/utils"
import { ai } from "@/ai"
import { AiActionsDrawer } from "@/components/AiActionsDrawer"

interface EmailViewerProps {
  selectedEmail: Email | null
  threadEmails: Email[]
  onEmailSent: () => void
  onDelete: () => void
}

export function EmailViewer({ selectedEmail, threadEmails, onEmailSent, onDelete }: EmailViewerProps) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [replyBody, setReplyBody] = useState("")
  const [draftLoading, setDraftLoading] = useState(false)
  const selectedRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (selectedRef.current) {
      selectedRef.current.scrollIntoView({ behavior: "smooth", block: "center" })
    }
  }, [selectedEmail?.id])

  if (!selectedEmail) {
    return (
      <Empty className="flex-1">
        <EmptyHeader>
          <EmptyTitle>No email selected</EmptyTitle>
          <EmptyDescription>
            Select an email from the sidebar to view its contents.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  const threadSubject = threadEmails[0]?.subject || selectedEmail.subject
  const latestEmail = threadEmails[threadEmails.length - 1] || selectedEmail

  const handleReply = () => {
    const replySubject = latestEmail.subject.startsWith("Re: ") ? latestEmail.subject : `Re: ${latestEmail.subject}`
    fetch(`${API_BASE}/emails`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sender: PRIMARY_USER,
        recipient: latestEmail.sender,
        subject: replySubject,
        body: replyBody,
        thread_id: selectedEmail.thread_id,
      }),
    }).then(() => {
      setReplyBody("")
      setDrawerOpen(false)
      onEmailSent()
    })
  }

  const handleAiDraft = () => {
    setDraftLoading(true)
    ai.draft(selectedEmail.thread_id)
      .then((d) => setReplyBody(d.body))
      .catch((e) => setReplyBody(`Error drafting reply: ${e instanceof Error ? e.message : String(e)}`))
      .finally(() => setDraftLoading(false))
  }

  const handleDelete = () => {
    fetch(`${API_BASE}/emails/${selectedEmail.id}`, { method: "DELETE" }).then(onDelete)
  }

  const handleMarkUnread = () => {
    fetch(`${API_BASE}/emails/${selectedEmail.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_read: false }),
    }).then(onDelete)
  }

  return (
    <>
      <div className="p-6 border-b flex justify-center">
        <div className="w-full max-w-[100ch]">
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-xl font-semibold">{threadSubject}</h2>
            <Badge variant="outline" className="text-xs">
              Thread: {selectedEmail.thread_id.slice(0, 8)}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              {threadEmails.length} {threadEmails.length === 1 ? "message" : "messages"}
            </div>
            <ButtonGroup>
            <AiActionsDrawer
              title="AI Insights"
              emptyHint="Pick an action to analyze this thread."
              trigger={
                <Button variant="outline" size="sm">
                  <Sparkles className="size-4" />
                </Button>
              }
              actions={[
                { label: "Summarize", run: () => ai.summarize(selectedEmail.thread_id) },
                { label: "Classify", run: () => ai.classify(selectedEmail.thread_id) },
                { label: "State", run: () => ai.state(selectedEmail.thread_id) },
                { label: "Urgency", run: () => ai.urgency(selectedEmail.thread_id) },
              ]}
            />
            <Drawer direction="right" open={drawerOpen} onOpenChange={setDrawerOpen}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <DrawerTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Reply className="size-4" />
                    </Button>
                  </DrawerTrigger>
                </TooltipTrigger>
                <TooltipContent>Reply</TooltipContent>
              </Tooltip>
              <DrawerContent>
                <DrawerHeader>
                  <DrawerTitle>Reply to {latestEmail.sender.split("@")[0]}</DrawerTitle>
                </DrawerHeader>
                <div className="flex flex-col gap-4 p-4">
                  <Button
                    variant="outline"
                    size="sm"
                    className="self-start"
                    disabled={draftLoading}
                    onClick={handleAiDraft}
                  >
                    {draftLoading ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <Sparkles className="size-4" />
                    )}
                    Draft with AI
                  </Button>
                  <Textarea
                    placeholder="Write your reply..."
                    value={replyBody}
                    onChange={(e) => setReplyBody(e.target.value)}
                    className="min-h-32"
                  />
                </div>
                <DrawerFooter>
                  <Button onClick={handleReply}>Send</Button>
                  <DrawerClose asChild>
                    <Button variant="outline">Cancel</Button>
                  </DrawerClose>
                </DrawerFooter>
              </DrawerContent>
            </Drawer>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="sm" onClick={handleMarkUnread}>
                  <Mail className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Mark as unread</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="sm" onClick={handleDelete}>
                  <Trash2 className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Delete</TooltipContent>
            </Tooltip>
          </ButtonGroup>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto flex justify-center">
        <div className="w-full max-w-[100ch]">
        {threadEmails.map((email, index) => (
          <div key={email.id}>
            <div
              ref={email.id === selectedEmail.id ? selectedRef : null}
              className={`p-6 ${email.id === selectedEmail.id ? "bg-accent/30" : ""}`}
            >
              <div className="flex items-start gap-4 mb-4">
                <Avatar size="lg">
                  <AvatarFallback>{getInitials(email.sender)}</AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <div className="font-medium">{email.sender}</div>
                    <div className="text-sm text-muted-foreground">to {email.recipient}</div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {formatDate(email.created_at)}
                  </div>
                </div>
              </div>
              <p className="whitespace-pre-wrap text-sm">{email.body}</p>
            </div>
            {index < threadEmails.length - 1 && <Separator />}
          </div>
        ))}
        </div>
      </div>
    </>
  )
}
