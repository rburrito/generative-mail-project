import { useState } from "react"
import {
  Item,
  ItemContent,
  ItemTitle,
  ItemDescription,
  ItemGroup,
  ItemSeparator,
} from "@/components/ui/item"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
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
import { Send, Plus } from "lucide-react"
import type { Email } from "@/types"
import { PRIMARY_USER, API_BASE } from "@/constants"
import { formatDate, getInitials } from "@/utils"

interface EmailListProps {
  emails: Email[]
  selectedEmail: Email | null
  onSelect: (email: Email) => void
  onEmailSent: () => void
}

export function EmailList({ emails, selectedEmail, onSelect, onEmailSent }: EmailListProps) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [recipient, setRecipient] = useState("")
  const [subject, setSubject] = useState("")
  const [body, setBody] = useState("")

  const handleSend = () => {
    fetch(`${API_BASE}/emails`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sender: PRIMARY_USER, recipient, subject, body }),
    }).then(() => {
      setRecipient("")
      setSubject("")
      setBody("")
      setDrawerOpen(false)
      onEmailSent()
    })
  }

  return (
    <aside className="w-80 border-r flex flex-col">
      <div className="p-4 border-b flex items-center justify-between">
        <h1 className="font-semibold">GenMail</h1>
        <Drawer direction="right" open={drawerOpen} onOpenChange={setDrawerOpen}>
          <DrawerTrigger asChild>
            <Button variant="ghost" size="icon">
              <Plus className="size-4" />
            </Button>
          </DrawerTrigger>
          <DrawerContent>
            <DrawerHeader>
              <DrawerTitle>New Email</DrawerTitle>
            </DrawerHeader>
            <div className="flex flex-col gap-4 p-4">
              <Input
                placeholder="Recipient"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
              />
              <Input
                placeholder="Subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
              />
              <Textarea
                placeholder="Message"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="min-h-32"
              />
            </div>
            <DrawerFooter>
              <Button onClick={handleSend}>Send</Button>
              <DrawerClose asChild>
                <Button variant="outline">Cancel</Button>
              </DrawerClose>
            </DrawerFooter>
          </DrawerContent>
        </Drawer>
      </div>
      <div className="flex-1 overflow-y-auto">
        <ItemGroup>
          {emails.map((email, index) => (
            <div key={email.id}>
              {index > 0 && <ItemSeparator />}
              <Item
                size="sm"
                className={`cursor-pointer hover:bg-accent/50 ${
                  selectedEmail?.id === email.id ? "bg-accent" : ""
                }`}
                onClick={() => onSelect(email)}
              >
                <Avatar>
                  <AvatarFallback>{getInitials(email.sender)}</AvatarFallback>
                </Avatar>
                <ItemContent>
                  <div className="flex items-center gap-2">
                    {!email.is_read && (
                      <div className="size-2 rounded-full bg-blue-500 shrink-0" />
                    )}
                    <ItemTitle className={`text-sm ${!email.is_read ? "font-bold" : ""}`}>
                      {email.sender.split("@")[0]}
                    </ItemTitle>
                  </div>
                  <ItemDescription className={`line-clamp-1 ${!email.is_read ? "font-semibold text-foreground" : "font-medium text-foreground"}`}>
                    {email.subject}
                  </ItemDescription>
                  <ItemDescription className="line-clamp-1">
                    {email.body}
                  </ItemDescription>
                </ItemContent>
                <div className="flex flex-col items-end shrink-0 gap-1">
                  <span className="text-xs text-muted-foreground">
                    {formatDate(email.created_at)}
                  </span>
                  {email.sender === PRIMARY_USER && (
                    <Send className="size-3 text-muted-foreground" />
                  )}
                </div>
              </Item>
            </div>
          ))}
        </ItemGroup>
      </div>
    </aside>
  )
}
