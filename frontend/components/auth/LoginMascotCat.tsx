"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  passwordFocused: boolean;
  isCyber: boolean;
  className?: string;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export default function LoginMascotCat({ passwordFocused, isCyber, className = "" }: Props) {
  const [pointer, setPointer] = useState({ x: 0, y: 0 });
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
      }
      frameRef.current = requestAnimationFrame(() => {
        const x = clamp((event.clientX / window.innerWidth) * 2 - 1, -1, 1);
        const y = clamp((event.clientY / window.innerHeight) * 2 - 1, -1, 1);
        setPointer({ x, y });
      });
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
      }
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  const headRotate = passwordFocused ? 0 : pointer.x * 7;
  const bodyRotate = passwordFocused ? -2 : pointer.x * 4;
  const tailRotate = passwordFocused ? -12 : pointer.x * 18;
  const pupilOffsetX = passwordFocused ? 0 : pointer.x * 5;
  const pupilOffsetY = passwordFocused ? 0 : pointer.y * 3;
  const whiskerOffset = passwordFocused ? 0 : pointer.x * 2;
  const pawOffset = passwordFocused ? -4 : pointer.y * -4;

  return (
    <div className={`flex flex-col items-center ${className}`}>
      <div
        className={`relative flex h-44 w-44 items-center justify-center rounded-[32px] border shadow-[0_20px_60px_rgba(15,23,42,0.18)] ${
          isCyber
            ? "border-cyan-400/20 bg-slate-950/70"
            : "border-slate-200 bg-white/85"
        }`}
      >
        <div
          className={`pointer-events-none absolute inset-4 rounded-[28px] ${
            isCyber
              ? "bg-[radial-gradient(circle_at_top,rgba(34,211,238,0.16),transparent_60%)]"
              : "bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.14),transparent_62%)]"
          }`}
        />

        <svg viewBox="0 0 220 220" className="relative z-10 h-36 w-36 overflow-visible">
          <g
            style={{
              transform: `rotate(${bodyRotate}deg)`,
              transformOrigin: "110px 128px",
              transition: "transform 160ms ease-out",
            }}
          >
            <path
              d="M164 144c18 6 28 20 28 36 0 10-3 17-9 22"
              fill="none"
              stroke={isCyber ? "#22D3EE" : "#334155"}
              strokeWidth="10"
              strokeLinecap="round"
              style={{
                transform: `rotate(${tailRotate}deg)`,
                transformOrigin: "164px 144px",
                transition: "transform 180ms ease-out",
              }}
            />
            <ellipse cx="110" cy="136" rx="58" ry="46" fill="#101318" />
            <ellipse cx="110" cy="142" rx="42" ry="24" fill={isCyber ? "#0F172A" : "#1E293B"} opacity="0.42" />
            <circle
              cx="76"
              cy="156"
              r="11"
              fill="#101318"
              style={{ transform: `translateY(${pawOffset}px)`, transition: "transform 160ms ease-out" }}
            />
            <circle cx="146" cy="156" r="11" fill="#101318" />
          </g>

          <g
            style={{
              transform: `rotate(${headRotate}deg)`,
              transformOrigin: "110px 94px",
              transition: "transform 160ms ease-out",
            }}
          >
            <path d="M72 56L92 28L104 62Z" fill="#101318" />
            <path d="M148 56L128 28L116 62Z" fill="#101318" />
            <path d="M80 50L92 33L98 56Z" fill={isCyber ? "#22D3EE" : "#60A5FA"} opacity="0.28" />
            <path d="M140 50L128 33L122 56Z" fill={isCyber ? "#22D3EE" : "#60A5FA"} opacity="0.28" />
            <circle cx="110" cy="92" r="42" fill="#111418" />
            <ellipse cx="110" cy="108" rx="24" ry="16" fill="#1F2937" opacity="0.42" />

            {passwordFocused ? (
              <>
                <path d="M87 93c6 5 14 5 20 0" fill="none" stroke="#E2E8F0" strokeWidth="4" strokeLinecap="round" />
                <path d="M113 93c6 5 14 5 20 0" fill="none" stroke="#E2E8F0" strokeWidth="4" strokeLinecap="round" />
              </>
            ) : (
              <>
                <ellipse cx="96" cy="91" rx="11" ry="13" fill="#F8FAFC" />
                <ellipse cx="124" cy="91" rx="11" ry="13" fill="#F8FAFC" />
                <circle
                  cx={96 + pupilOffsetX}
                  cy={91 + pupilOffsetY}
                  r="5"
                  fill={isCyber ? "#22D3EE" : "#1D4ED8"}
                  style={{ transition: "cx 120ms ease-out, cy 120ms ease-out" }}
                />
                <circle
                  cx={124 + pupilOffsetX}
                  cy={91 + pupilOffsetY}
                  r="5"
                  fill={isCyber ? "#22D3EE" : "#1D4ED8"}
                  style={{ transition: "cx 120ms ease-out, cy 120ms ease-out" }}
                />
              </>
            )}

            <path d="M110 100l-8 8h16l-8-8Z" fill={isCyber ? "#22D3EE" : "#60A5FA"} />
            <path d="M104 109c2 5 10 5 12 0" fill="none" stroke="#E2E8F0" strokeWidth="3" strokeLinecap="round" />
            <path
              d={`M64 ${102 + whiskerOffset}c12-3 22-3 34 1`}
              fill="none"
              stroke="#CBD5E1"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <path
              d={`M64 ${112 + whiskerOffset}c13 1 22 2 32 7`}
              fill="none"
              stroke="#CBD5E1"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <path
              d={`M156 ${102 - whiskerOffset}c-12-3-22-3-34 1`}
              fill="none"
              stroke="#CBD5E1"
              strokeWidth="3"
              strokeLinecap="round"
            />
            <path
              d={`M156 ${112 - whiskerOffset}c-13 1-22 2-32 7`}
              fill="none"
              stroke="#CBD5E1"
              strokeWidth="3"
              strokeLinecap="round"
            />
          </g>
        </svg>
      </div>

      <div
        className={`mt-3 rounded-full border px-4 py-2 text-xs font-medium ${
          isCyber
            ? "border-cyan-400/20 bg-cyan-400/10 text-cyan-100"
            : "border-slate-200 bg-white/80 text-slate-600"
        }`}
      >
        {passwordFocused ? "小黑猫正在闭眼帮你保密" : "小黑猫会跟着你的鼠标看向不同方向"}
      </div>
    </div>
  );
}
