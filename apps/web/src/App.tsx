import { Route, Routes } from "react-router-dom";
import { RequireActiveSession, RequireAdmin, RequireAuth } from "./components/RouteGuards";
import { SiteFooter } from "./components/SiteFooter";
import { SiteNavbar } from "./components/SiteNavbar";
import { AboutPage } from "./pages/AboutPage";
import { AdminAssignmentsPage } from "./pages/AdminAssignmentsPage";
import { AdminAuditPage } from "./pages/AdminAuditPage";
import { AdminCatalogPage } from "./pages/AdminCatalogPage";
import { AdminEvaluationsPage } from "./pages/AdminEvaluationsPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { ContactPage } from "./pages/ContactPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { MyProfilePage } from "./pages/MyProfilePage";
import { MyScenariosPage } from "./pages/MyScenariosPage";
import { PublicScenarioPage } from "./pages/PublicScenarioPage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { ScenarioEditorPage } from "./pages/ScenarioEditorPage";
import { SignupPage } from "./pages/SignupPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";

export function App() {
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <SiteNavbar />
      <div className="app-shell__body">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/contact" element={<ContactPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/my-scenarios"
            element={
              <RequireAuth>
                <MyScenariosPage />
              </RequireAuth>
            }
          />
          <Route
            path="/my-profile"
            element={
              <RequireAuth>
                <MyProfilePage />
              </RequireAuth>
            }
          />
          <Route
            path="/scenarios/new"
            element={
              <RequireAuth>
                <RequireActiveSession>
                  <ScenarioEditorPage isCreate />
                </RequireActiveSession>
              </RequireAuth>
            }
          />
          <Route
            path="/scenarios/:id/edit"
            element={
              <RequireAuth>
                <RequireActiveSession>
                  <ScenarioEditorPage />
                </RequireActiveSession>
              </RequireAuth>
            }
          />
          <Route
            path="/scenarios/:id/view"
            element={
              <RequireAuth>
                <ScenarioEditorPage viewOnly />
              </RequireAuth>
            }
          />
          <Route
            path="/review"
            element={
              <RequireAuth>
                <RequireActiveSession>
                  <ReviewQueuePage />
                </RequireActiveSession>
              </RequireAuth>
            }
          />
          <Route
            path="/admin/users"
            element={
              <RequireAuth>
                <RequireAdmin>
                  <AdminUsersPage />
                </RequireAdmin>
              </RequireAuth>
            }
          />
          <Route
            path="/admin/catalogs"
            element={
              <RequireAuth>
                <RequireAdmin>
                  <AdminCatalogPage />
                </RequireAdmin>
              </RequireAuth>
            }
          />
          <Route
            path="/admin/assignments"
            element={
              <RequireAuth>
                <RequireAdmin>
                  <AdminAssignmentsPage />
                </RequireAdmin>
              </RequireAuth>
            }
          />
          <Route
            path="/admin/evaluations"
            element={
              <RequireAuth>
                <RequireAdmin>
                  <AdminEvaluationsPage />
                </RequireAdmin>
              </RequireAuth>
            }
          />
          <Route
            path="/admin/audit"
            element={
              <RequireAuth>
                <RequireAdmin>
                  <AdminAuditPage />
                </RequireAdmin>
              </RequireAuth>
            }
          />
          <Route path="/public/:slug" element={<PublicScenarioPage />} />
        </Routes>
      </div>
      <SiteFooter />
    </div>
  );
}
