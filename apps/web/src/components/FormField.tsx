import { type InputHTMLAttributes, type TextareaHTMLAttributes, useId } from "react";

type BaseProps = {
  label: string;
  hint?: string;
  hideLabel?: boolean;
};

type InputProps = BaseProps & {
  multiline?: false;
} & InputHTMLAttributes<HTMLInputElement>;

type TextareaProps = BaseProps & {
  multiline: true;
} & TextareaHTMLAttributes<HTMLTextAreaElement>;

export function FormField(props: InputProps | TextareaProps) {
  const id = useId();
  const { label, hint, hideLabel, multiline, ...fieldProps } = props;

  return (
    <div className="form-field">
      <label htmlFor={id} className={hideLabel ? "sr-only" : undefined}>
        {label}
      </label>
      {hint ? <p className="form-field__hint">{hint}</p> : null}
      {multiline ? (
        <textarea id={id} {...(fieldProps as TextareaHTMLAttributes<HTMLTextAreaElement>)} />
      ) : (
        <input id={id} {...(fieldProps as InputHTMLAttributes<HTMLInputElement>)} />
      )}
    </div>
  );
}
