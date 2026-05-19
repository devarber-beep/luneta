import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  assignInvestigator,
  listAdminUsers,
  listReviewerInvestigators,
  unassignInvestigator,
  type AdminUserSummary,
} from "../adminApi";
import { getToken } from "../session";

const layoutStyle = { maxWidth: "720px", margin: "0 auto", padding: "2rem", fontFamily: "system-ui, sans-serif" };

export function AdminAssignmentsPage() {
  const token = getToken() ?? "";
  const [reviewers, setReviewers] = useState<AdminUserSummary[]>([]);
  const [investigators, setInvestigators] = useState<AdminUserSummary[]>([]);
  const [selectedReviewerId, setSelectedReviewerId] = useState("");
  const [assignedIds, setAssignedIds] = useState<string[]>([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([listAdminUsers(token, "reviewer"), listAdminUsers(token, "investigator")])
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

  const investigatorName = (id: string) => investigators.find((i) => i.user_id === id)?.nickname ?? id;

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
    <main style={layoutStyle}>
      <h2>Admin — reviewer assignments</h2>
      <p>
        <Link to="/admin/catalogs">Catalogs</Link> · <Link to="/">Home</Link>
      </p>
      <label style={{ display: "grid", gap: "0.25rem", marginBottom: "1rem" }}>
        <span>Reviewer</span>
        <select value={selectedReviewerId} onChange={(e) => setSelectedReviewerId(e.target.value)}>
          {reviewers.map((r) => (
            <option key={r.user_id} value={r.user_id}>
              {r.nickname} ({r.email_normalized})
            </option>
          ))}
        </select>
      </label>

      <section style={{ marginBottom: "1.5rem" }}>
        <h3>Assigned investigators</h3>
        {!assignedIds.length ? <p>None assigned yet.</p> : null}
        <ul style={{ paddingLeft: "1.25rem" }}>
          {assignedIds.map((id) => (
            <li key={id} style={{ marginBottom: "0.35rem" }}>
              {investigatorName(id)}{" "}
              <button type="button" onClick={() => void onUnassign(id)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Add investigator</h3>
        {!unassigned.length ? <p>All investigators are already assigned to this reviewer.</p> : null}
        <ul style={{ paddingLeft: "1.25rem" }}>
          {unassigned.map((inv) => (
            <li key={inv.user_id} style={{ marginBottom: "0.35rem" }}>
              {inv.nickname}{" "}
              <button type="button" onClick={() => void onAssign(inv.user_id)}>
                Assign
              </button>
            </li>
          ))}
        </ul>
      </section>

      {message ? <p style={{ color: "crimson", marginTop: "1rem" }}>{message}</p> : null}
    </main>
  );
}
