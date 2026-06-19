import { PageLayout } from "../components/PageLayout";

export function ContactPage() {
  return (
    <PageLayout documentTitle="Contact" heading="Contact">
      <div className="card prose-block">
        <p>
          For questions about the consortium or this platform, contact Juan Pablo Hourcade at{" "}
          <a href="mailto:juanpablo-hourcade@uiowa.edu">juanpablo-hourcade@uiowa.edu</a>.
        </p>
        <p>
          More information is available on the{" "}
          <a href="https://jphourcade.com/projects/xrforyouthethics/index.html" rel="noreferrer" target="_blank">
            consortium website
          </a>
          .
        </p>
      </div>
    </PageLayout>
  );
}
