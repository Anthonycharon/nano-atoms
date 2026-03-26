import type { ComponentProps } from "react";

type Props = ComponentProps<"svg">;

export default function AtomBrandMark({ className, ...props }: Props) {
  return (
    <svg
      viewBox="0 0 128 128"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      {...props}
    >
      <defs>
        <linearGradient id="atom-bg" x1="16" y1="12" x2="112" y2="116" gradientUnits="userSpaceOnUse">
          <stop stopColor="#F8FCFF" />
          <stop offset="1" stopColor="#CFE4FF" />
        </linearGradient>
        <linearGradient id="atom-ring" x1="26" y1="24" x2="104" y2="104" gradientUnits="userSpaceOnUse">
          <stop stopColor="#8ED0FF" />
          <stop offset="0.48" stopColor="#2563EB" />
          <stop offset="1" stopColor="#0F172A" />
        </linearGradient>
        <radialGradient id="atom-core" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(64 64) rotate(90) scale(24)">
          <stop stopColor="#FFFFFF" />
          <stop offset="0.58" stopColor="#38BDF8" />
          <stop offset="1" stopColor="#0F172A" />
        </radialGradient>
      </defs>
      <rect x="6" y="6" width="116" height="116" rx="30" fill="url(#atom-bg)" />
      <g stroke="url(#atom-ring)" strokeWidth="4.5" strokeLinecap="round">
        <ellipse cx="64" cy="64" rx="42" ry="18" transform="rotate(18 64 64)" />
        <ellipse cx="64" cy="64" rx="42" ry="18" transform="rotate(90 64 64)" />
        <ellipse cx="64" cy="64" rx="42" ry="18" transform="rotate(-36 64 64)" />
      </g>
      <g fill="url(#atom-core)">
        <circle cx="64" cy="64" r="14" />
        <circle cx="37" cy="44" r="5.5" />
        <circle cx="89" cy="42" r="5.5" />
        <circle cx="94" cy="81" r="5.5" />
        <circle cx="47" cy="92" r="5.5" />
        <circle cx="69" cy="28" r="4.5" />
        <circle cx="56" cy="79" r="4" />
      </g>
    </svg>
  );
}
