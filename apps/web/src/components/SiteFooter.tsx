import { Link } from "react-router-dom";

const CONSORTIUM_URL = "https://jphourcade.com/projects/xrforyouthethics/index.html";
const UGR_URL = "https://www.ugr.es/en";
const PARTNER_UNIVERSITY_URL = "https://uiowa.edu/";

export function SiteFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <nav className="site-footer__nav" aria-label="Footer">
          <Link to="/about">About</Link>
          <Link to="/contact">Contact</Link>
          <a href={CONSORTIUM_URL} rel="noreferrer" target="_blank">
            XR for Youth Ethics Consortium
          </a>
          <a href={UGR_URL} rel="noreferrer" target="_blank">
            Universidad de Granada
          </a>
          <a href={PARTNER_UNIVERSITY_URL} rel="noreferrer" target="_blank">
            University of Iowa
          </a>
        </nav>
        <p className="site-footer__copy">
          © {year} XR for Youth Ethics Consortium
        </p>
      </div>
    </footer>
  );
}
