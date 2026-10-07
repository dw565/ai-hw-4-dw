/** Tiny pixel-art renderer: each string is a row, each character a pixel. '.' is empty. */
interface Props {
  rows: string[]
  palette: Record<string, string>
  pixel?: number // CSS px per art pixel
  className?: string
  title?: string
}

export default function PixelArt({ rows, palette, pixel = 4, className, title }: Props) {
  const width = Math.max(...rows.map((r) => r.length))
  const rects = []
  for (let y = 0; y < rows.length; y++) {
    for (let x = 0; x < rows[y].length; x++) {
      const color = palette[rows[y][x]]
      if (color) rects.push(<rect key={`${x}-${y}`} x={x} y={y} width={1} height={1} fill={color} />)
    }
  }
  return (
    <svg
      className={className}
      viewBox={`0 0 ${width} ${rows.length}`}
      width={width * pixel}
      height={rows.length * pixel}
      shapeRendering="crispEdges"
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      {rects}
    </svg>
  )
}

const YALE = { D: '#00254a', B: '#00356b', L: '#286dc0', W: '#ffffff', K: '#0b0f1a', P: '#f2a7b5' }
// Dan gets a dark outline and a lighter sweater so he reads on Yale-blue backgrounds too.
const DAN = { ...YALE, D: '#0b1a2e', B: '#4f9be8' }

/** Handsome Dan in a Yale-blue sweater, facing right. Two frames for a walk cycle. */
const DAN_TOP = [
  '............DD..DD..',
  '...........DWWDDWWD.',
  '...........DWWWWWWWD',
  '...........DWWWKWWWD',
  '...........DWWWWWWKD',
  '..D........DWWWWWWWD',
  '.DWD.DDDDDDDBBWPWWD.',
  '..DDDBBBBBBBBBBDDD..',
  '...DBBBBWWBBBBBBD...',
  '...DBBBBWWBBBBBBD...',
]
export const DAN_FRAME_A = [
  ...DAN_TOP,
  '...DWWDDDDDDDDWWD...',
  '...DWWD......DWWD...',
  '...DDDD......DDDD...',
]
export const DAN_FRAME_B = [
  ...DAN_TOP,
  '...DDWWDDDDDDWWDD...',
  '....DWWD....DWWD....',
  '....DDDD....DDDD....',
]

export function Bulldog({ pixel = 4, frame = 'A' }: { pixel?: number; frame?: 'A' | 'B' }) {
  return <PixelArt rows={frame === 'A' ? DAN_FRAME_A : DAN_FRAME_B} palette={DAN} pixel={pixel} />
}

/** Harkness Tower silhouette. */
const HARKNESS = [
  '.....W.....',
  '.....W.....',
  '....WWW....',
  '...W.W.W...',
  '...WWWWW...',
  '...W.W.W...',
  '..WWWWWWW..',
  '..W.W.W.W..',
  '..WWWWWWW..',
  '.WWWWWWWWW.',
  '.W.WW.WW.W.',
  '.W.WW.WW.W.',
  '.WWWWWWWWW.',
  '.WW.WWW.WW.',
  '.WW.WWW.WW.',
  '.WWWWWWWWW.',
  'WWWWWWWWWWW',
  'WW.WW.WW.WW',
  'WW.WW.WW.WW',
  'WWWWWWWWWWW',
  'WW.WW.WW.WW',
  'WW.WW.WW.WW',
  'WWWWWWWWWWW',
  'WWWW...WWWW',
  'WWWW...WWWW',
]
export function HarknessTower({ pixel = 6 }: { pixel?: number }) {
  return <PixelArt rows={HARKNESS} palette={{ W: 'rgba(255,255,255,0.22)' }} pixel={pixel} />
}

/** 8x8 pixel "Y" logo. */
const Y_LOGO = [
  'BBBBBBBB',
  'BWWBBWWB',
  'BWWBBWWB',
  'BBWWWWBB',
  'BBBWWBBB',
  'BBBWWBBB',
  'BBBWWBBB',
  'BBBBBBBB',
]
export function PixelLogo({ pixel = 5 }: { pixel?: number }) {
  return <PixelArt rows={Y_LOGO} palette={YALE} pixel={pixel} title="Campus Customs" />
}
