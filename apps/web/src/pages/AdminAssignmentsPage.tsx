import { useEffect, useState } from "react";import {
  assignInvestigator,
  listAdminUsers,
  listReviewerInvestigators,
  unassignInvestigator,
  type AdminUserSummary,
} from "../adminApi";
import { getToken } from "../session";
import { PageLayout } from "../components/PageLayout";
import { StatusMessage } from "../components/StatusMessage";

export function AdminAssignmentsPage() {
  const token = getToken() ?? "";
  const [reviewers, setReviewers] = useState<AdminUserSummary[]>([]);
  const [investigators, setInvestigators] = useState<AdminUserSummary[]>([]);
  const [selectedReviewerId, setSelectedReviewerId] = useState("");
  const [assignedIds, setAssignedIds] = useState<string[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([
      listAdminUsers(token, { role: "reviewer" }),
      listAdminUsers(token, { role: "investigator" }),
    ])
      .then(([revs, invs]) => {
        setReviewers(revs);
        setInvestigators(invs);
        if (revs.length && !selectedReviewerId) {
          setSelectedReviewerId(revs[0].user_id);
        }
      })
      .catch((e: Error) => setMessage(e.message));
  }, []);

  useEffect(() => {
    if (!selectedReviewerId) {
      setAssignedIds([]);
      return;
    }
    listReviewerInvestigators(token, selectedReviewerId)
      .then((res) => setAssignedIds(res.investigator_user_ids))
      .catch((e: Error) => setMessage(e.message));
  }, [selectedReviewerId, token]);

  const investigatorName = (id: string) => investigators.find((i) => i.user_id === id)?.display_name ?? id;

  const onAssign = async (investigatorId: string) => {
    try {
      await assignInvestigator(token, selectedReviewerId, investigatorId);
      const res = await listReviewerInvestigators(token, selectedReviewerId);
      setAssignedIds(res.investigator_user_ids);
      setMessage("Assignment saved.");
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  const onUnassign = async (investigatorId: string) => {
    try {
      await unassignInvestigator(token, selectedReviewerId, investigatorId);
      const res = await listReviewerInvestigators(token, selectedReviewerId);
      setAssignedIds(res.investigator_user_ids);
      setMessage("Assignment removed.");
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  const unassigned = investigators.filter((i) => !assignedIds.includes(i.user_id));

  return (
    <PageLayout documentTitle="Assignments" heading="">
      <label className="form-field" style={{ maxWidth: "28rem", marginBottom: "1rem" }}>
        <span>Reviewer</span>
        <select value={selectedReviewerId} onChange={(e) => setSelectedReviewerId(e.target.value)}>
          {reviewers.map((r) => (
            <option key={r.user_id} value={r.user_id}>
              {r.display_name} ({r.email_normalized})
            </option>
          ))}
        </select>
      </label>

      <section style={{ marginBottom: "1.5rem" }}>
        <h3>Assigned investigators</h3>
        {!assignedIds.length ? <p>None assigned yet.</p> : null}
        <ul className="assignment-list">
          {assignedIds.map((id) => (
            <li key={id} className="assignment-list__item">
              <span>{investigatorName(id)}</span>
              <button type="button" className="btn btn--danger" onClick={() => void onUnassign(id)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Add investigator</h3>
        {!unassigned.length ? <p>All investigators are already assigned to this reviewer.</p> : null}
        <ul className="assignment-list">
          {unassigned.map((inv) => (
            <li key={inv.user_id} className="assignment-list__item">
              <span>{inv.display_name}</span>
              <button type="button" className="btn btn--primary" onClick={() => void onAssign(inv.user_id)}>
                Assign
              </button>
            </li>
          ))}
        </ul>
      </section>

      <StatusMessage message={message} onDismiss={() => setMessage("")} />
    </PageLayout>
  );
}
