import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, type Product } from '../api'
import HeroScene from '../components/HeroScene'
import ProductCard from '../components/ProductCard'

const categories = [
  { label: 'Hoodies', value: 'hoodie', blurb: 'Heavyweight layers for January in New Haven.' },
  { label: 'Crewnecks', value: 'sweatshirt', blurb: 'The classic Yale sweatshirt, in more than one shade of blue.' },
  { label: 'T-shirts', value: 't-shirt', blurb: 'Game-day graphics and everyday tees.' },
  { label: 'Quarter-zips', value: 'quarter-zip', blurb: 'Dress it up for the office or the tailgate.' },
]

export default function Home() {
  const [featured, setFeatured] = useState<Product[]>([])

  useEffect(() => {
    fetchProducts()
      .then((all) => setFeatured(all.filter((p) => p.total_stock > 0).slice(0, 4)))
      .catch(() => setFeatured([]))
  }, [])

  return (
    <>
      <section className="hero">
        <HeroScene />
        <div className="hero-inner">
          <p className="eyebrow">Player 1 · Official Yale gear · New Haven</p>
          <h1>Wear your Bulldog pride every day.</h1>
          <p className="hero-sub">
            Hoodies, crewnecks, tees, and quarter-zips for students, alumni, families,
            and anyone who bleeds Yale blue. Browse the shop, or ask our assistant to
            help you find the right fit.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-light">
              ▶ Start shopping
            </Link>
            <Link to="/about" className="btn btn-ghost">
              Our story
            </Link>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>Shop by style</h2>
        <div className="category-grid">
          {categories.map((c) => (
            <Link to={`/products?category=${encodeURIComponent(c.value)}`} key={c.label} className="category-tile">
              <h3>
                {c.label} <span className="tile-arrow">▶</span>
              </h3>
              <p>{c.blurb}</p>
            </Link>
          ))}
        </div>
      </section>

      {featured.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2>Fresh picks</h2>
            <Link to="/products">View all →</Link>
          </div>
          <div className="product-grid">
            {featured.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </section>
      )}

      <section className="section callout">
        <h2>Need a hint?</h2>
        <p>
          Open the chat in the corner and tell us what you're looking for — a gift for a
          new Eli, something for The Game, or a hoodie in your size.
        </p>
      </section>
    </>
  )
}
