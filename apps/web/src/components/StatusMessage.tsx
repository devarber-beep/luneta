import { type ReactNode } from "react";
import { AlertModal, type AlertVariant } from "./AlertModal";

type Variant = AlertVariant;

type Presentation = "inline" | "modal" | "auto";

type Props = {
  message: string;
  variant?: Variant;
  presentation?: Presentation;
  title?: string;
  children?: ReactNode;
  onDismiss?: () => void;
};

function looksLikeSuccess(message: string): boolean {
  const lower = message.toLowerCase();
  const hints = [
    "saved",
    "updated",
    "verified",
    "submitted",
    "published",
    "deleted.",
    "thank",
    "created",
    "removed",
    "applied",
    "accepted",
    "signed in",
    "sent to",
    "you can now",
    "opened",
    "marked not suitable",
    "hidden",
    "assignment saved",
    "assignment removed",
    "entry created",
    "photo updated",
    "photo removed",
    "password updated",
    "profile saved",
    "draft deleted",
    "evaluation submitted",
    "role updated",
    "account status updated",
    "alternative text applied",
    "suggestion accepted",
    "suggestion rejected",
    "suggestion submitted",
    "discarded",
    "generated",
  ];
  return hints.some((hint) => lower.includes(hint));
}

function looksLikeWarning(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    lower.includes("warning") ||
    lower.includes("similar published") ||
    lower.includes("similar scenario") ||
    lower.includes("sensitive") ||
    lower.includes("identifiable") ||
    lower.includes("review before") ||
    lower.includes("not saved yet")
  );
}

function looksLikeError(message: string): boolean {
  if (looksLikeSuccess(message) || looksLikeWarning(message)) {
    return false;
  }
  const lower = message.toLowerCase();
  const hints = [
    "error",
    "failed",
    "failure",
    "invalid",
    "cannot ",
    "can't ",
    "could not",
    "unable",
    "not found",
    "unauthorized",
    "forbidden",
    "do not match",
    "cannot be empty",
    "wrong",
    "denied",
    "expired",
    "incorrect",
    "missing",
    "not allowed",
    "no permission",
    "are required",
    "is required",
    "must have",
    "must be",
    "at least",
    "select at least",
  ];
  return hints.some((hint) => lower.includes(hint));
}

function inferVariant(message: string): Variant {
  const lower = message.toLowerCase();
  if (looksLikeWarning(message)) {
    return "warning";
  }
  if (looksLikeSuccess(message)) {
    return "success";
  }
  if (lower.includes("loading")) {
    return "info";
  }
  if (looksLikeError(message)) {
    return "error";
  }
  return "info";
}

function inferTitle(message: string, variant: Variant): string {
  const firstLine = message.split("\n")[0].trim();

  if (variant === "warning") {
    return "Please review";
  }
  if (variant === "success") {
    return "Done";
  }
  if (variant === "info") {
    return firstLine.length <= 80 ? firstLine : "Notice";
  }

  const lower = firstLine.toLowerCase();
  if (
    lower.includes("required") ||
    lower.includes("must ") ||
    lower.includes("cannot be empty") ||
    lower.includes("at least") ||
    lower.includes("do not match") ||
    lower.includes("select at least")
  ) {
    return "Check your input";
  }
  if (firstLine.length <= 80) {
    return firstLine;
  }
  return "Error";
}

function modalMessageBody(message: string, resolvedTitle: string): string {
  if (!message) {
    return "";
  }
  const firstLine = message.split("\n")[0].trim();
  if (message === firstLine && resolvedTitle === firstLine) {
    return "";
  }
  if (message.startsWith(firstLine) && resolvedTitle === firstLine && message.length > firstLine.length) {
    return message.slice(firstLine.length).replace(/^\s+/, "");
  }
  return message;
}

function shouldUseModal(resolved: Variant, presentation: Presentation): boolean {
  if (presentation === "inline") {
    return false;
  }
  if (presentation === "modal") {
    return true;
  }
  return resolved === "error" || resolved === "warning";
}

export function StatusMessage({
  message,
  variant,
  presentation = "auto",
  title,
  children,
  onDismiss,
}: Props) {
  if (!message && !children) {
    return null;
  }

  const resolved = variant ?? inferVariant(message);
  const useModal = shouldUseModal(resolved, presentation);

  if (useModal && onDismiss) {
    const resolvedTitle = title ?? inferTitle(message, resolved);
    const modalMessage = title ? message : modalMessageBody(message, resolvedTitle);

    return (
      <AlertModal
        title={resolvedTitle}
        message={modalMessage}
        variant={resolved}
        onClose={onDismiss}
      >
        {children}
      </AlertModal>
    );
  }

  if (!message) {
    return null;
  }

  return (
    <p className={`status-message status-message--${resolved}`} role="status" aria-live="polite">
      {message}
    </p>
  );
}
