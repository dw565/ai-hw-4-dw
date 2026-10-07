import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          <strong>Campus Customs</strong>
          <p>57 Broadway, New Haven, CT 06511</p>
        </div>
        <div className="footer-links">
          <Link to="/products">Shop</Link>
          <Link to="/about">About Us</Link>
          <Link to="/login">Log in</Link>
        </div>
        <p className="footer-note">
          Class project for Foundations of AI. Not affiliated with the real store.
        </p>
      </div>
    </footer>
  )
}
