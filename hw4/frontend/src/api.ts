export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  price: number
  image_url: string
  total_stock: number
  category: string
  sizes_in_stock: string[]
}

export interface StockLevel {
  size: string
  quantity: number
}

export interface ProductDetail extends Product {
  inventory: StockLevel[]
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const fetchProducts = () => getJson<Product[]>('/api/products')

export const fetchProduct = (id: string) =>
  getJson<ProductDetail>(`/api/products/${encodeURIComponent(id)}`)

export const formatPrice = (price: number) => `$${price.toFixed(2)}`

// The fields a product card needs; both catalogue products and chat cards have them.
export type CardProduct = Pick<
  Product,
  | 'product_id'
  | 'name'
  | 'description'
  | 'price'
  | 'image_url'
  | 'total_stock'
  | 'category'
  | 'sizes_in_stock'
>

export interface ProductCardData extends CardProduct {
  garment_type: string
  colors: string[]
}

export interface CatalogueQuery {
  query?: string
  category?: string | null
  color?: string | null
  min_price?: number | null
  max_price?: number | null
  size?: string | null
  in_stock_only?: boolean
}

export interface PageResults {
  title: string
  search: CatalogueQuery
  total: number
  products: ProductCardData[]
}

const SEARCH_KEYS = [
  'query',
  'category',
  'color',
  'min_price',
  'max_price',
  'size',
  'in_stock_only',
] as const

/** URL params for a chat search, e.g. ?title=Hoodies&category=hoodie. Empty values are dropped. */
export function pageResultsParams(title: string, search: CatalogueQuery): URLSearchParams {
  const params = new URLSearchParams({ title })
  for (const key of SEARCH_KEYS) {
    const value = search[key]
    if (value !== undefined && value !== null && value !== '' && value !== false)
      params.set(key, String(value))
  }
  return params
}

/** Re-run a chat search from the Products page URL (used after a reload or shared link). */
export function fetchPageResults(params: URLSearchParams) {
  return getJson<PageResults>(`/api/search?${params.toString()}`)
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  reply: string
  products: ProductCardData[]
  page_results: PageResults | null
  facts_checked: number
}

export type PageType =
  | 'home'
  | 'products'
  | 'product'
  | 'about'
  | 'login'
  | 'create-account'
  | 'other'

/** What the shopper is looking at, sent with every chat message. */
export interface PageContext {
  path: string
  page_type: PageType
  product_id?: string
  results_title?: string
  results_search?: CatalogueQuery
}

export interface SavedMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  products: ProductCardData[]
  created_at: string
}

const authHeader = (token: string | null): Record<string, string> =>
  token ? { Authorization: `Bearer ${token}` } : {}

export async function sendChat(
  message: string,
  history: ChatTurn[],
  token: string | null,
  page: PageContext,
): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader(token) },
    body: JSON.stringify({ message, history, page }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(
      typeof body?.detail === 'string' ? body.detail : 'The assistant is unavailable right now.',
    )
  }
  return res.json() as Promise<ChatResponse>
}

export async function fetchChatHistory(token: string): Promise<SavedMessage[]> {
  const res = await fetch('/api/chat/history', { headers: authHeader(token) })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json() as Promise<SavedMessage[]>
}

export async function clearChatHistory(token: string): Promise<void> {
  await fetch('/api/chat/history', { method: 'DELETE', headers: authHeader(token) })
}
