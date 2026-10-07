import { Bulldog, HarknessTower } from './PixelArt'

/** Decorative campus scene for the Home hero: Harkness Tower, twinkling stars,
 * and Handsome Dan walking along the ground. Hidden from screen readers. */
export default function HeroScene() {
  return (
    <div className="hero-scene" aria-hidden="true">
      <div className="hero-stars">
        {Array.from({ length: 14 }, (_, i) => (
          <span key={i} style={{ left: `${(i * 37) % 100}%`, top: `${(i * 53) % 60}%`, animationDelay: `${(i % 5) * 0.6}s` }} />
        ))}
      </div>
      <div className="hero-tower">
        <HarknessTower pixel={7} />
      </div>
      <div className="hero-ground" />
      <div className="hero-dan">
        <div className="hero-dan-flip">
          <span className="dan-frame dan-a">
            <Bulldog frame="A" pixel={4} />
          </span>
          <span className="dan-frame dan-b">
            <Bulldog frame="B" pixel={4} />
          </span>
        </div>
      </div>
    </div>
  )
}
