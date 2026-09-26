import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

/**
 * FI-TAX — Executive Enterprise Brand Logo
 * Crafted with golden-ratio precision:
 * Continuous geometric sapphire ribbon + electric indigo prism + precision emerald statutory node.
 */
export default function Logo({ size = 32, showText = true, className, animate = false }) {
  const Emblem = (
    <svg
      width={size}
      height={size}
      viewBox="0 0 44 44"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="flex-shrink-0"
    >
      <defs>
        {/* Sapphire Primary Gradient */}
        <linearGradient id="emblem-sapphire" x1="2" y1="4" x2="42" y2="40" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#1E40AF" />
          <stop offset="45%" stopColor="#2563EB" />
          <stop offset="100%" stopColor="#3B82F6" />
        </linearGradient>

        {/* Electric Accent Gradient */}
        <linearGradient id="emblem-accent" x1="14" y1="6" x2="38" y2="30" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#60A5FA" />
          <stop offset="100%" stopColor="#2563EB" />
        </linearGradient>

        {/* Statutory Emerald Node */}
        <linearGradient id="emblem-emerald" x1="26" y1="4" x2="38" y2="16" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#34D399" />
          <stop offset="100%" stopColor="#059669" />
        </linearGradient>

        {/* Ambient shadow */}
        <filter id="emblem-shadow" x="-10%" y="-10%" width="125%" height="125%" filterUnits="userSpaceOnUse">
          <feDropShadow dx="0" dy="2.5" stdDeviation="3" floodColor="#1E40AF" floodOpacity="0.25" />
        </filter>
      </defs>

      <g filter="url(#emblem-shadow)">
        {/* Base Squircle Foundation */}
        <rect
          x="3"
          y="3"
          width="38"
          height="38"
          rx="11"
          fill="url(#emblem-sapphire)"
        />

        {/* Architectural Monogram Layer: Continuous "F" & "T" Interlocking Balance Beams */}
        {/* Upper horizontal ledger */}
        <path
          d="M12 13.5H31C31.8 13.5 32.5 14.2 32.5 15C32.5 15.8 31.8 16.5 31 16.5H12C11.2 16.5 10.5 15.8 10.5 15C10.5 14.2 11.2 13.5 12 13.5Z"
          fill="white"
        />

        {/* Central Vertical Pillar */}
        <path
          d="M20 15V29.5C20 30.3 19.3 31 18.5 31C17.7 31 17 30.3 17 29.5V15H20Z"
          fill="white"
          fillOpacity="0.95"
        />

        {/* Dynamic Middle Balance Step ("F" crossbar / statutory shelf) */}
        <path
          d="M18.5 21.5H27C27.8 21.5 28.5 22.2 28.5 23C28.5 23.8 27.8 24.5 27 24.5H18.5V21.5Z"
          fill="white"
          fillOpacity="0.9"
        />

        {/* Precision Statutory Check Node (Emerald Orbit) */}
        <circle
          cx="31.5"
          cy="12.5"
          r="4.5"
          fill="url(#emblem-emerald)"
          stroke="#FFFFFF"
          strokeWidth="2"
        />
        <circle cx="31.5" cy="12.5" r="1.5" fill="#FFFFFF" />
      </g>
    </svg>
  )

  return (
    <div className={cn('flex items-center gap-3 select-none', className)}>
      {animate ? (
        <motion.div
          whileHover={{ scale: 1.06, rotate: -1.5 }}
          whileTap={{ scale: 0.94 }}
          transition={{ type: 'spring', stiffness: 400, damping: 22 }}
          className="cursor-pointer"
        >
          {Emblem}
        </motion.div>
      ) : (
        Emblem
      )}

      {showText && (
        <div className="flex flex-col leading-none">
          <div className="flex items-center gap-2">
            <span className="text-[16px] font-extrabold tracking-tight text-gray-900 font-sans">
              FI<span className="text-blue-600">·TAX</span>
            </span>
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 border border-emerald-200/90 px-1.5 py-0.5 rounded shadow-2xs">
              S/4HANA
            </span>
          </div>
          <span className="text-[11px] font-medium text-gray-500 tracking-normal mt-1">
            GST Compliance Intel
          </span>
        </div>
      )}
    </div>
  )
}
