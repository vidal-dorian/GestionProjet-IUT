import { type KeyboardEvent, type PointerEvent, useRef, useState } from "react";
import type { Balance } from "../api/reports";

/* Même repère et même géométrie que l'image insérée dans le daily exporté
   (backend/app/docx_charts.py) : le point placé ici tombe au même endroit
   dans le Word. */
const WIDTH = 1000;
const HEIGHT = 820;
const RADIUS = 160;
const CIRCLES = [
  { cx: 400, cy: 330 },
  { cx: 600, cy: 330 },
  { cx: 500, cy: 500 },
];

// Positions des anciennes zones prédéfinies (dailies enregistrés avant le placement libre).
const PRESET_POINTS: Record<Balance, { x: number; y: number }> = {
  all: { x: 500, y: 387 },
  time_quality: { x: 500, y: 270 },
  time_scope: { x: 407, y: 440 },
  quality_scope: { x: 593, y: 440 },
  time: { x: 320, y: 290 },
  quality: { x: 680, y: 290 },
  scope: { x: 500, y: 590 },
};

const KEYBOARD_STEP = 10;

interface Props {
  x: number | null | undefined;
  y: number | null | undefined;
  balance: Balance | undefined;
  onChange: (point: { x: number; y: number }) => void;
}

function clamp(value: number, max: number): number {
  return Math.round(Math.min(Math.max(value, 0), max));
}

export default function BalanceDiagram({ x, y, balance, onChange }: Props) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const point = x != null && y != null ? { x, y } : PRESET_POINTS[balance ?? "all"];

  function pointFromEvent(event: PointerEvent<SVGSVGElement>) {
    const svg = svgRef.current;
    const matrix = svg?.getScreenCTM();
    if (!svg || !matrix) return null;
    const transformed = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
    return { x: clamp(transformed.x, WIDTH), y: clamp(transformed.y, HEIGHT) };
  }

  function handlePointerDown(event: PointerEvent<SVGSVGElement>) {
    const next = pointFromEvent(event);
    if (!next) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(true);
    onChange(next);
  }

  function handlePointerMove(event: PointerEvent<SVGSVGElement>) {
    if (!dragging) return;
    const next = pointFromEvent(event);
    if (next) onChange(next);
  }

  function handleKeyDown(event: KeyboardEvent<SVGSVGElement>) {
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [-KEYBOARD_STEP, 0],
      ArrowRight: [KEYBOARD_STEP, 0],
      ArrowUp: [0, -KEYBOARD_STEP],
      ArrowDown: [0, KEYBOARD_STEP],
    };
    const move = moves[event.key];
    if (!move) return;
    event.preventDefault();
    onChange({ x: clamp(point.x + move[0], WIDTH), y: clamp(point.y + move[1], HEIGHT) });
  }

  return (
    <div className="balance-diagram">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="application"
        aria-label="Position du projet entre temps, qualité et respect du cahier des charges. Cliquer ou glisser pour déplacer le point rouge, ou utiliser les flèches du clavier."
        tabIndex={0}
        className={dragging ? "is-dragging" : undefined}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={() => setDragging(false)}
        onPointerCancel={() => setDragging(false)}
        onKeyDown={handleKeyDown}
      >
        <rect width={WIDTH} height={HEIGHT} className="balance-diagram-bg" />
        {CIRCLES.map((circle) => (
          <circle key={`${circle.cx}-${circle.cy}`} cx={circle.cx} cy={circle.cy} r={RADIUS} className="balance-diagram-circle" />
        ))}
        <text x={150} y={195} className="balance-diagram-label">
          Temps
        </text>
        <text x={850} y={195} className="balance-diagram-label">
          Qualité
        </text>
        <text x={500} y={725} className="balance-diagram-label">
          Respect du cahier des
        </text>
        <text x={500} y={780} className="balance-diagram-label">
          charges
        </text>
        <circle cx={point.x} cy={point.y} r={14} className="balance-diagram-dot" />
      </svg>
    </div>
  );
}
