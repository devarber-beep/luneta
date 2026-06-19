import { type ReactNode } from "react";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

type Props = {
  children: ReactNode;
  /** Sets document.title and optional visible heading when title is omitted. */
  documentTitle?: string;
  /** Visible page heading; omit or pass empty string to hide. */
  heading?: string;
  headingLevel?: 1 | 2;
  className?: string;
  /** Optional actions aligned to the top-right of the page heading row. */
  headerAside?: ReactNode;
};

export function PageLayout({
  children,
  documentTitle,
  heading,
  headingLevel = 2,
  className,
  headerAside,
}: Props) {
  const visibleHeading = heading === undefined ? documentTitle : heading;
  useDocumentTitle(documentTitle ?? visibleHeading);

  const HeadingTag = headingLevel === 1 ? "h1" : "h2";

  return (
    <main id="main-content" className={`page-layout${className ? ` ${className}` : ""}`} tabIndex={-1}>
      {headerAside && visibleHeading ? (
        <div className="page-layout__header page-layout__header--with-aside">
          <HeadingTag className="page-layout__heading">{visibleHeading}</HeadingTag>
          <div className="page-layout__header-aside">{headerAside}</div>
        </div>
      ) : visibleHeading ? (
        <HeadingTag>{visibleHeading}</HeadingTag>
      ) : null}
      {children}
    </main>
  );
}
