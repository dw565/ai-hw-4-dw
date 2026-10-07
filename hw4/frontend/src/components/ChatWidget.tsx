import { useEffect, useRef, useState, type FormEvent } from 'react'
import Markdown from 'react-markdown'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  clearChatHistory,
  fetchChatHistory,
  formatPrice,
  pageResultsParams,
  sendChat,
  type ChatTurn,
  type PageResults,
  type ProductCardData,
} from '../api'
import { useAuth } from '../auth'
import { useChatUi } from '../chatUi'
import { pageContextFor } from '../pageContext'
import { suggestionsFor } from '../suggestions'

interface ChatMessage extends ChatTurn {
  products?: ProductCardData[]
  pageResults?: PageResults
  error?: boolean
  greeting?: boolean // local only; never sent to the agent
  factsChecked?: number
}

function greeting(firstName?: string, returning = false): ChatMessage {
  const content = !firstName
    ? "Hi! I'm the Campus Customs assistant. Ask me about hoodies, tees, sizes, or prices."
    : returning
      ? `Welcome back, ${firstName}! Your earlier chat is below. What can I help you find today?`
      : `Hi ${firstName}! I'm the Campus Customs assistant. Ask me about hoodies, tees, sizes, or prices.`
  return { role: 'assistant', content, greeting: true }
}

function ChatProductCard({ product }: { product: ProductCardData }) {
  return (
    <Link to={`/products/${product.product_id}`} className="chat-card">
      <img src={product.image_url} alt={product.name} />
      <div>
        <strong>{product.name}</strong>
        <span className="price">{formatPrice(product.price)}</span>
        {product.total_stock === 0 && <span className="error">Sold out</span>}
      </div>
    </Link>
  )
}

export default function ChatWidget() {
  const { user, token } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { open, setOpen } = useChatUi()
  const [messages, setMessages] = useState<ChatMessage[]>([greeting()])
  const [input, setInput] = useState('')
  const [pending, setPending] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open, pending])

  // Signed in: reload saved history from the server. Signed out: start a fresh guest chat.
  useEffect(() => {
    if (!user || !token) {
      setMessages([greeting()])
      return
    }
    let cancelled = false
    fetchChatHistory(token)
      .then((saved) => {
        if (cancelled) return
        setMessages([
          greeting(user.first_name, saved.length > 0),
          ...saved.map((m) => ({ role: m.role, content: m.content, products: m.products })),
        ])
      })
      .catch(() => !cancelled && setMessages([greeting(user.first_name)]))
    return () => {
      cancelled = true
    }
  }, [user, token])

  async function handleClear() {
    if (!token || !window.confirm('Clear your saved chat history?')) return
    await clearChatHistory(token)
    setMessages([greeting(user?.first_name)])
  }

  // Put a chat search's matches into the Products page grid.
  function showOnPage(results: PageResults) {
    const params = pageResultsParams(results.title, results.search)
    navigate(`/products?${params}`, {
      state: { pageResults: results, resultsKey: params.toString() },
    })
  }

  const page = pageContextFor(location.pathname, location.search)
  const suggestions = suggestionsFor(page)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    send(input)
  }

  async function send(raw: string) {
    const text = raw.trim()
    if (!text || pending) return
    // Signed-in history is loaded from the database on the server, so only guests send it.
    // It excludes the local greeting and any error bubbles.
    const history: ChatTurn[] = user
      ? []
      : messages.filter((m) => !m.greeting && !m.error).map(({ role, content }) => ({ role, content }))
    setMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setPending(true)
    try {
      const res = await sendChat(text, history, token, page)
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: res.reply,
          products: res.products,
          pageResults: res.page_results ?? undefined,
          factsChecked: res.facts_checked,
        },
      ])
      if (res.page_results) showOnPage(res.page_results)
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: (err as Error).message, error: true },
      ])
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Chat with Campus Customs">
          <header className="chat-header">
            <div>
              <strong>Campus Customs Assistant</strong>
              <small>
                {user
                  ? `Signed in as ${user.first_name} · chat saved`
                  : 'Guest chat · log in to save it'}
              </small>
            </div>
            {user && (
              <button className="chat-clear" onClick={handleClear} title="Clear saved chat">
                Clear
              </button>
            )}
            <button
              className="chat-close"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
            >
              ×
            </button>
          </header>
          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className={`chat-row chat-row-${m.role}`}>
                <div className={`chat-msg chat-msg-${m.role}${m.error ? ' chat-msg-error' : ''}`}>
                  {m.role === 'assistant' ? <Markdown>{m.content}</Markdown> : m.content}
                </div>
                {m.factsChecked ? (
                  <span className="chat-verified" title="Every price and stock count in this reply was checked against live inventory">
                    ✓ Prices &amp; stock checked against live inventory
                  </span>
                ) : null}
                {m.pageResults && (
                  <button className="chat-page-link" onClick={() => showOnPage(m.pageResults!)}>
                    📄 {m.pageResults.total} {m.pageResults.total === 1 ? 'match' : 'matches'} on
                    the page: {m.pageResults.title} →
                  </button>
                )}
                {m.products && m.products.length > 0 && (
                  <div className="chat-cards">
                    {m.products.map((p) => (
                      <ChatProductCard key={p.product_id} product={p} />
                    ))}
                  </div>
                )}
              </div>
            ))}
            {pending && (
              <div className="chat-msg chat-msg-assistant typing" aria-label="Assistant is typing">
                <span />
                <span />
                <span />
              </div>
            )}
            <div ref={endRef} />
          </div>
          {!pending && !input && (
            <div className="chat-suggestions" aria-label="Suggested questions">
              {suggestions.map((q) => (
                <button key={q} className="chat-suggestion" onClick={() => send(q)}>
                  {q}
                </button>
              ))}
            </div>
          )}
          <form className="chat-input" onSubmit={handleSubmit}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about a hoodie, size, or price…"
              aria-label="Message"
              maxLength={2000}
            />
            <button type="submit" disabled={!input.trim() || pending}>
              Send
            </button>
          </form>
        </section>
      )}
      <button
        className="chat-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? 'Close chat' : 'Open chat'}
      >
        {open ? '✕' : '💬 Chat'}
      </button>
    </div>
  )
}
