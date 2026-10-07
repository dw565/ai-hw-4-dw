import { Link } from 'react-router-dom'
import { formatPrice, type CardProduct } from '../api'

export default function ProductCard({ product }: { product: CardProduct }) {
  const soldOut = product.total_stock === 0
  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {soldOut && <span className="badge">Sold out</span>}
        <span className="card-cta" aria-hidden="true">View ▶</span>
      </div>
      <div className="product-card-body">
        <h3>{product.name}</h3>
        <p className="price">{formatPrice(product.price)}</p>
        <p className="product-card-desc">{product.description}</p>
      </div>
    </Link>
  )
}
