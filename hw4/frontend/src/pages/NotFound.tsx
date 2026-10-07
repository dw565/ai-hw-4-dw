import { Link } from 'react-router-dom'
import { Bulldog } from '../components/PixelArt'

export default function NotFound() {
  return (
    <section className="section game-over">
      <Bulldog pixel={6} />
      <h1>Game over</h1>
      <p className="muted">That page doesn't exist.</p>
      <Link to="/" className="btn">
        ▶ Continue
      </Link>
    </section>
  )
}
