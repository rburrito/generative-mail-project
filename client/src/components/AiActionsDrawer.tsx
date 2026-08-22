import { useState, type ReactNode } from "react"
import { Button } from "@/components/ui/button"
import {
  Drawer,
  DrawerTrigger,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import { Loader2 } from "lucide-react"

export type AiAction = { label: string; run: () => Promise<string> }

interface AiActionsDrawerProps {
  trigger: ReactNode
  title: string
  actions: AiAction[]
  emptyHint: string
}

/** A right-side drawer that runs AI actions and shows their text output. Reused
 * for both thread-scoped insights and the global inbox intelligence bar. */
export function AiActionsDrawer({ trigger, title, actions, emptyHint }: AiActionsDrawerProps) {
  const [loadingLabel, setLoadingLabel] = useState<string | null>(null)
  const [resultLabel, setResultLabel] = useState("")
  const [output, setOutput] = useState("")

  const run = async (action: AiAction) => {
    setLoadingLabel(action.label)
    setOutput("")
    try {
      const text = await action.run()
      setResultLabel(action.label)
      setOutput(text)
    } catch (e) {
      setResultLabel(action.label)
      setOutput(`Error: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setLoadingLabel(null)
    }
  }

  return (
    <Drawer direction="right">
      <DrawerTrigger asChild>{trigger}</DrawerTrigger>
      <DrawerContent>
        <DrawerHeader>
          <DrawerTitle>{title}</DrawerTitle>
        </DrawerHeader>
        <div className="flex flex-wrap gap-2 px-4 pb-3">
          {actions.map((action) => (
            <Button
              key={action.label}
              variant="outline"
              size="sm"
              disabled={loadingLabel !== null}
              onClick={() => run(action)}
            >
              {action.label}
            </Button>
          ))}
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
            <div className="text-sm text-muted-foreground">{emptyHint}</div>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  )
}
