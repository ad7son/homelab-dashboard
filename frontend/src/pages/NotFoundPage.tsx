import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="dashboard">
      <h1>Page not found</h1>
      <p>
        <Link to="/homelab">Back to Home Lab</Link>
      </p>
    </div>
  );
}
