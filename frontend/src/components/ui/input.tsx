import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    // Accessibility floor: if a consumer renders an Input without an associated
    // <label> (no id+htmlFor), an aria-label, or an aria-labelledby, fall back
    // to the placeholder as the accessible name so screen-reader users aren't
    // left with an unlabeled field. An explicit label always wins.
    const hasName =
      props["aria-label"] != null ||
      props["aria-labelledby"] != null ||
      props.id != null;
    const derivedAriaLabel =
      !hasName && typeof props.placeholder === "string"
        ? props.placeholder
        : undefined;

    return (
      <input
        type={type}
        aria-label={derivedAriaLabel}
        className={cn(
          "flex h-9 w-full rounded-md border border-slate-300 bg-white px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
