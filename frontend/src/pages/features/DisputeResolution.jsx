import { Link } from "react-router-dom";

export default function DisputeResolution() {
  return (
    <main className="max-w-3xl mx-auto px-4 py-12">
      <Link to="/dashboard" className="text-sm text-navy hover:text-gold">
        ← Back to dashboard
      </Link>
      <h1 className="text-3xl font-bold text-navy mt-4 mb-4">Dispute Resolution</h1>
      <div className="card">
        <p className="text-slateDalil/70">
          Coming soon — dispute submission and mediation will be wired here.
        </p>
      </div>
    </main>
  );
}