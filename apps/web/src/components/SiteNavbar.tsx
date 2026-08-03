import { Link, useLocation } from "react-router-dom";
import { useRole, useToken } from "../useSession";
import { UserMenu } from "./UserMenu";

const BRAND = "XR for Youth Ethics Consortium";

export function SiteNavbar() {
  const token = useToken();
  const role = useRole();
  const location = useLocation();

  const linkClass = (path: string) =>
    `site-navbar__link${location.pathname === path ? " site-navbar__link--active" : ""}`;

  return (
    <header className="site-navbar">
      <div className="site-navbar__inner">
        <div className="site-navbar__brand">
          <Link to="/" className="site-navbar__brand-link">
            <img
              src="/logo_luneta.webp"
              alt=""
              aria-hidden="true"
              className="site-navbar__logo"
              width={72}
              height={72}
            />
            <span className="site-navbar__brand-text">{BRAND}</span>
          </Link>
        </div>
        <nav className="site-navbar__nav" aria-label="Main">
          <Link to="/" className={linkClass("/")}>
            Home
          </Link>
          {!token ? (
            <>
              <Link to="/signup" className={linkClass("/signup")}>
                Signup
              </Link>
              <Link to="/login" className={linkClass("/login")}>
                Login
              </Link>
            </>
          ) : null}
          {token ? (
            <Link to="/my-scenarios" className={linkClass("/my-scenarios")}>
              My Scenarios
            </Link>
          ) : null}
          {token ? (
            <Link to="/scenarios/new" className={linkClass("/scenarios/new")}>
              New Scenario
            </Link>
          ) : null}
          {role === "reviewer" || role === "admin" ? (
            <Link to="/review" className={linkClass("/review")}>
              Review
            </Link>
          ) : null}
          {role === "admin" ? (
            <>
              <Link to="/admin/users" className={linkClass("/admin/users")}>
                Users
              </Link>
              <Link to="/admin/catalogs" className={linkClass("/admin/catalogs")}>
                Risk Catalog
              </Link>
              <Link to="/admin/assignments" className={linkClass("/admin/assignments")}>
                Reviewers Assignment
              </Link>
              <Link to="/admin/evaluations" className={linkClass("/admin/evaluations")}>
                Evaluations
              </Link>
              <Link to="/admin/audit" className={linkClass("/admin/audit")}>
                Activity Log
              </Link>
            </>
          ) : null}
        </nav>
        {token ? (
          <div className="site-navbar__actions">
            <UserMenu />
          </div>
        ) : null}
      </div>
    </header>
  );
}
