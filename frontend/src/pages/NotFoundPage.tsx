import { Link } from "react-router-dom";

import { EmptyState } from "../components/QueryState";

export function NotFoundPage() {
  return (
    <EmptyState title="Page not found">
      <Link to="/" className="text-blue-300 hover:underline">Go to the dashboard</Link>
    </EmptyState>
  );
}
