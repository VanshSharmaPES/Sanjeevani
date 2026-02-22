const SanjeevaniLogo = ({ size = 48, breathing = false }: { size?: number; breathing?: boolean }) => {
  return (
    <div className={breathing ? "breathing" : ""}>
      <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
        {/* Leaf shape */}
        <path
          d="M32 6 Q52 20 48 40 Q44 56 32 58 Q20 56 16 40 Q12 20 32 6Z"
          fill="hsl(var(--forest))"
          stroke="hsl(var(--cyan))"
          strokeWidth="1.5"
        />
        {/* Circuit lines inside leaf */}
        <path d="M32 14 L32 50" stroke="hsl(var(--cyan))" strokeWidth="1" opacity="0.7" />
        <path d="M32 22 L40 28 L40 36" stroke="hsl(var(--cyan))" strokeWidth="0.8" opacity="0.6" />
        <path d="M32 22 L24 28 L24 36" stroke="hsl(var(--cyan))" strokeWidth="0.8" opacity="0.6" />
        <path d="M32 34 L38 38" stroke="hsl(var(--cyan))" strokeWidth="0.8" opacity="0.5" />
        <path d="M32 34 L26 38" stroke="hsl(var(--cyan))" strokeWidth="0.8" opacity="0.5" />
        {/* Circuit nodes */}
        <circle cx="32" cy="22" r="2" fill="hsl(var(--cyan))" />
        <circle cx="40" cy="28" r="1.5" fill="hsl(var(--saffron))" />
        <circle cx="24" cy="28" r="1.5" fill="hsl(var(--saffron))" />
        <circle cx="32" cy="34" r="2" fill="hsl(var(--cyan))" />
        <circle cx="32" cy="46" r="2.5" fill="hsl(var(--saffron))" />
        {/* Outer glow */}
        <path
          d="M32 6 Q52 20 48 40 Q44 56 32 58 Q20 56 16 40 Q12 20 32 6Z"
          fill="none"
          stroke="hsl(var(--cyan))"
          strokeWidth="0.5"
          opacity="0.3"
          filter="url(#glow)"
        />
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
      </svg>
    </div>
  );
};

export default SanjeevaniLogo;
