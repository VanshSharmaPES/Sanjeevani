const DNASpinner = () => {
  return (
    <div className="flex items-center justify-center">
      <svg className="dna-spin" width="40" height="40" viewBox="0 0 40 40">
        <circle cx="20" cy="4" r="3" fill="hsl(var(--saffron))" opacity="0.9" />
        <circle cx="20" cy="36" r="3" fill="hsl(var(--cyan))" opacity="0.9" />
        <circle cx="4" cy="20" r="2.5" fill="hsl(var(--cyan))" opacity="0.7" />
        <circle cx="36" cy="20" r="2.5" fill="hsl(var(--saffron))" opacity="0.7" />
        <path d="M20 4 Q36 12 36 20 Q36 28 20 36" fill="none" stroke="hsl(var(--saffron))" strokeWidth="1.5" opacity="0.6" />
        <path d="M20 4 Q4 12 4 20 Q4 28 20 36" fill="none" stroke="hsl(var(--cyan))" strokeWidth="1.5" opacity="0.6" />
        <line x1="8" y1="12" x2="32" y2="12" stroke="hsl(var(--foreground))" strokeWidth="0.5" opacity="0.3" />
        <line x1="4" y1="20" x2="36" y2="20" stroke="hsl(var(--foreground))" strokeWidth="0.5" opacity="0.3" />
        <line x1="8" y1="28" x2="32" y2="28" stroke="hsl(var(--foreground))" strokeWidth="0.5" opacity="0.3" />
      </svg>
    </div>
  );
};

export default DNASpinner;
