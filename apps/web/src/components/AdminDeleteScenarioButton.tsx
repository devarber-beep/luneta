import { useState } from "react";
import { deleteScenario } from "../api";
import { ConfirmModal } from "./ConfirmModal";

type Props = {
  scenarioId: string;
  title: string;
  token: string;
  onDeleted: () => void;
  onError?: (message: string) => void;
  label?: string;
};

export function AdminDeleteScenarioButton({
  scenarioId,
  title,
  token,
  onDeleted,
  onError,
  label = "Delete scenario",
}: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const executeDelete = async () => {
    setBusy(true);
    try {
      await deleteScenario(token, scenarioId);
      setOpen(false);
      onDeleted();
    } catch (error) {
      onError?.((error as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button type="button" className="btn btn--danger" onClick={() => setOpen(true)}>
        {label}
      </button>
      {open ? (
        <ConfirmModal
          title="Delete scenario?"
          message={`“${title}” will disappear from the public catalog. Stored images will be removed. This cannot be undone.`}
          variant="warning"
          confirmLabel="Delete scenario"
          confirmTone="danger"
          busy={busy}
          onConfirm={() => executeDelete()}
          onCancel={() => {
            if (!busy) {
              setOpen(false);
            }
          }}
        />
      ) : null}
    </>
  );
}
