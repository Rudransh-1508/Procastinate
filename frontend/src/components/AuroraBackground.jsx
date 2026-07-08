// Soft, static, warm ambient backdrop — organic, not "AI aurora".
export default function AuroraBackground({ className = "" }) {
  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden>
      {/* warm sage wash, top */}
      <div className="absolute -left-32 -top-40 h-[34rem] w-[34rem] rounded-full bg-brand/10 blur-[130px]" />
      {/* soft clay, lower right */}
      <div className="absolute -right-24 top-24 h-[28rem] w-[28rem] rounded-full bg-clay/[0.07] blur-[130px]" />
      {/* gentle top vignette to seat the hero */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 70% 50% at 50% -10%, rgba(140,160,106,0.06), transparent 70%)",
        }}
      />
    </div>
  );
}
