import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, type ProductDetail } from '../api'
import { useChatUi } from '../chatUi'

function stockLabel(qty: number) {
  if (qty === 0) return 'Sold out'
  if (qty <= 5) return `Only ${qty} left`
  return 'In stock'
}

const stockClass = (qty: number) => (qty === 0 ? 'out' : qty <= 5 ? 'low' : 'ok')

export default function ProductPage() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { setOpen } = useChatUi()

  useEffect(() => {
    setProduct(null)
    setError(null)
    fetchProduct(productId)
      .then(setProduct)
      .catch((e: Error) => setError(e.message))
  }, [productId])

  if (error)
    return (
      <section className="section">
        <p className="error">Couldn't load this product ({error}).</p>
        <Link to="/products">← Back to products</Link>
      </section>
    )
  if (!product) return <section className="section muted">Loading…</section>

  return (
    <section className="section">
      <Link to="/products" className="back-link">
        ← Back to products
      </Link>
      <div className="product-detail">
        <div className="product-detail-image">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="product-detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="price price-large">{formatPrice(product.price)}</p>
          <p>{product.description}</p>

          <h3>Colors</h3>
          <div className="chips">
            {product.colors.map((c) => (
              <span key={c} className="chip">
                {c}
              </span>
            ))}
          </div>

          <h3>Sizes &amp; stock</h3>
          <ul className="size-grid">
            {product.inventory.map((s) => (
              <li key={s.size} className={`size-tile ${stockClass(s.quantity)}`}>
                <span className="size-name">{s.size}</span>
                <span className="size-status">{stockLabel(s.quantity)}</span>
                {s.quantity > 5 && <span className="size-qty">{s.quantity} available</span>}
              </li>
            ))}
          </ul>

          <div className="ask-item">
            <div>
              <strong>Questions about this item?</strong>
              <span>Ask our assistant about sizes, stock, or similar styles.</span>
            </div>
            <button className="btn btn-small" onClick={() => setOpen(true)}>
              💬 Ask about this item
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
