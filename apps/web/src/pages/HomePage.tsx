import { PageLayout } from "../components/PageLayout";
import { PublishedScenariosSection } from "../components/PublishedScenariosSection";

export function HomePage() {
  return (
    <PageLayout documentTitle="Home" heading="Published scenarios" headingLevel={2}>
      <PublishedScenariosSection
        sectionHeading=""
        searchPlaceholder="Search by title, description, author or university"
      />
    </PageLayout>
  );
}
