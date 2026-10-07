import { createContext, useContext, useState, type ReactNode } from 'react'

/** Lets any page open the chat panel (e.g. "Ask about this item" on a product page). */
interface ChatUi {
  open: boolean
  setOpen: (open: boolean | ((o: boolean) => boolean)) => void
}

const ChatUiContext = createContext<ChatUi | null>(null)

export function ChatUiProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return <ChatUiContext.Provider value={{ open, setOpen }}>{children}</ChatUiContext.Provider>
}

export function useChatUi() {
  const ctx = useContext(ChatUiContext)
  if (!ctx) throw new Error('useChatUi must be used inside ChatUiProvider')
  return ctx
}
