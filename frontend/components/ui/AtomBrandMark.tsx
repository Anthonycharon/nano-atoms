import type { ComponentProps } from "react";

type Props = Omit<ComponentProps<"img">, "src" | "alt">;

export default function AtomBrandMark({ className, ...props }: Props) {
  return (
    <img
      src="/brand-logo.png"
      alt="Nano Atoms"
      className={className}
      {...props}
    />
  );
}
