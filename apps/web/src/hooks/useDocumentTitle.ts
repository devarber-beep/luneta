import { useEffect } from "react";

const BASE_TITLE = "XR for Youth Ethics Consortium";

export function useDocumentTitle(pageTitle?: string) {
  useEffect(() => {
    document.title = pageTitle ? `${pageTitle} · ${BASE_TITLE}` : BASE_TITLE;
  }, [pageTitle]);
}
