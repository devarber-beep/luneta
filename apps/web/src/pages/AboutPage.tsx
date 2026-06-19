import { PageLayout } from "../components/PageLayout";

export function AboutPage() {
  return (
    <PageLayout documentTitle="About" heading="About">
      <div className="card prose-block">
        <p>
          This platform supports the collection, review, and publication of smart-glasses usage scenarios in
          childhood contexts, as part of the{" "}
          <a href="https://jphourcade.com/projects/xrforyouthethics/index.html" rel="noreferrer" target="_blank">
            XR for Youth Ethics Consortium
          </a>
          .
        </p>
      </div>
    </PageLayout>
  );
}
