import { useEffect, useRef } from "react";

const MandalaBackground = () => {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {/* Mandala pattern - sacred geometry */}
      <svg
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 mandala-spin opacity-[0.06]"
        width="900"
        height="900"
        viewBox="0 0 900 900"
      >
        {/* Outer rings */}
        {[0, 30, 60, 90, 120, 150].map((angle) => (
          <g key={angle} transform={`rotate(${angle} 450 450)`}>
            <ellipse cx="450" cy="450" rx="400" ry="200" fill="none" stroke="hsl(168 100% 41%)" strokeWidth="0.5" />
          </g>
        ))}
        {/* Inner circles */}
        {[100, 180, 260, 340].map((r) => (
          <circle key={r} cx="450" cy="450" r={r} fill="none" stroke="hsl(38 90% 48%)" strokeWidth="0.3" opacity="0.5" />
        ))}
        {/* Petals */}
        {Array.from({ length: 12 }).map((_, i) => (
          <g key={`p-${i}`} transform={`rotate(${i * 30} 450 450)`}>
            <path
              d="M450 450 Q480 300 450 150 Q420 300 450 450"
              fill="none"
              stroke="hsl(168 100% 41%)"
              strokeWidth="0.4"
              opacity="0.6"
            />
          </g>
        ))}
        {/* Sacred dots */}
        {Array.from({ length: 8 }).map((_, i) => {
          const angle = (i * 45 * Math.PI) / 180;
          const cx = 450 + Math.cos(angle) * 320;
          const cy = 450 + Math.sin(angle) * 320;
          return <circle key={`d-${i}`} cx={cx} cy={cy} r="3" fill="hsl(38 90% 48%)" opacity="0.4" />;
        })}
      </svg>
    </div>
  );
};

export default MandalaBackground;
