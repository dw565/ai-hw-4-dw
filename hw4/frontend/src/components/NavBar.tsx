import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { PixelLogo } from './PixelArt'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  return (
    <header className="navbar">
      <div className="announcement">
        <span className="blink">★</span> Official Yale gear · Visit us at 57 Broadway, New Haven{' '}
        <span className="blink">★</span>
      </div>
      <nav className="nav-inner">
        <Link to="/" className="brand">
          <span className="brand-mark">
            <PixelLogo pixel={5} />
          </span>
          <span className="brand-text">
            Campus Customs
            <small>Bulldog Blue Shop</small>
          </span>
        </Link>
        <ul className="nav-links">
          {links.map((l) => (
            <li key={l.to}>
              <NavLink to={l.to} end={l.end}>
                {l.label}
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="nav-account">
          {user ? (
            <>
              <span className="nav-greeting">Hi, {user.first_name}</span>
              <button
                className="btn btn-small btn-outline"
                onClick={() => {
                  logout()
                  navigate('/')
                }}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login">Log in</NavLink>
              <NavLink to="/create-account" className="btn btn-small">
                Create account
              </NavLink>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
