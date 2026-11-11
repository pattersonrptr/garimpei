import Link from "next/link";

import { SearchForm } from "@/components/SearchForm";

export function TopBar({
  query,
  withSearch = true,
}: {
  query?: string;
  withSearch?: boolean;
}) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Link href="/" className="brand">
          Garimpei
        </Link>
        {withSearch && <SearchForm defaultValue={query} />}
      </div>
    </header>
  );
}
