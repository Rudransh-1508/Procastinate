// Count-up number that animates to its target on mount / when value changes.
// Respects reduced-motion (snaps to final value).
import { useEffect } from "react";
import {
  useMotionValue,
  useTransform,
  animate,
  useReducedMotion,
} from "framer-motion";
import { motion } from "framer-motion";

export default function AnimatedNumber({ value, decimals = 0, className }) {
  const reduce = useReducedMotion();
  const mv = useMotionValue(0);
  const rounded = useTransform(mv, (v) =>
    decimals ? v.toFixed(decimals) : Math.round(v).toString()
  );

  useEffect(() => {
    if (reduce) {
      mv.set(value);
      return;
    }
    const controls = animate(mv, value, { duration: 0.7, ease: [0.22, 1, 0.36, 1] });
    return controls.stop;
  }, [value, reduce, mv]);

  return <motion.span className={className}>{rounded}</motion.span>;
}
