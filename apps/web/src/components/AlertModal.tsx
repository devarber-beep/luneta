import { type ReactNode, useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";

export type AlertVariant = "error" | "success" | "warning" | "info";

const DEFAULT_TITLES: Record<AlertVariant, string> = {
  error: "Error",
  success: "Done",
  warning: "Please review",
  info: "Notice",
};

type Props = {
  title?: string;
  message: string;
  variant?: AlertVariant;
  children?: ReactNode;
  onClose: () => void;
};

export function AlertModal({ title, message, variant = "error", children, onClose }: Props) {
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose]);

  return createPortal(
    <div className="alert-modal" role="presentation" onClick={onClose}>
      <div
        className={`alert-modal__dialog alert-modal__dialog--${variant}`}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
      >
        <div className={`alert-modal__badge alert-modal__badge--${variant}`} aria-hidden>
          {variant === "success" ? "✓" : variant === "warning" ? "!" : variant === "info" ? "i" : "×"}
        </div>
        <h2 id={titleId} className="alert-modal__title">
          {title ?? DEFAULT_TITLES[variant]}
        </h2>
        {message ? <p className="alert-modal__message">{message}</p> : null}
        {children ? <div className="alert-modal__body">{children}</div> : null}
        <button
          ref={closeRef}
          type="button"
          className={`btn alert-modal__close alert-modal__close--${variant}`}
          onClick={onClose}
        >
          <span className="alert-modal__close-icon" aria-hidden>
            ×
          </span>
          Close
        </button>
      </div>
    </div>,
    document.body,
  );
}
