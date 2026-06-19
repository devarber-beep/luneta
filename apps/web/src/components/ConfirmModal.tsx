import { useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";
import type { AlertVariant } from "./AlertModal";

type Props = {
  title: string;
  message: string;
  variant?: AlertVariant;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmTone?: "primary" | "danger";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmModal({
  title,
  message,
  variant = "warning",
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  confirmTone = "primary",
  busy = false,
  onConfirm,
  onCancel,
}: Props) {
  const titleId = useId();
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    cancelRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) {
        onCancel();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [busy, onCancel]);

  const confirmClassName =
    confirmTone === "danger" ? "btn btn--danger alert-modal__confirm" : "btn btn--primary alert-modal__confirm";

  return createPortal(
    <div className="alert-modal" role="presentation" onClick={busy ? undefined : onCancel}>
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
          {title}
        </h2>
        {message ? <p className="alert-modal__message">{message}</p> : null}
        <div className="alert-modal__actions">
          <button ref={cancelRef} type="button" className="btn alert-modal__cancel" disabled={busy} onClick={onCancel}>
            {cancelLabel}
          </button>
          <button type="button" className={confirmClassName} disabled={busy} onClick={onConfirm}>
            {busy ? "Working…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
