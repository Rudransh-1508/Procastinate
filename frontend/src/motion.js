// Shared framer-motion variants. Keep durations in the 150–320ms band and
// use transform/opacity only (performant, no layout thrash).

export const EASE = [0.22, 1, 0.36, 1];

export const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: 0.04 },
  },
};

export const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.32, ease: EASE } },
};

export const bubble = {
  hidden: { opacity: 0, y: 10, scale: 0.98 },
  show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.26, ease: EASE } },
};

// hover lift for cards
export const hoverLift = {
  rest: { y: 0 },
  hover: { y: -3, transition: { duration: 0.18, ease: EASE } },
};
