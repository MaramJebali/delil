import { Navigate, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import OfficerRoute from "./components/OfficerRoute.jsx";

import Landing from "./pages/Landing.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import OfficerDashboard from "./pages/admin/OfficerDashboard.jsx";
import ContractUnderstanding from "./pages/features/ContractUnderstanding.jsx";
import WorkflowGuidance from "./pages/features/WorkflowGuidance.jsx";
import DisputeResolution from "./pages/features/DisputeResolution.jsx";

export default function App() {
  return (
    <div className="min-h-screen bg-cream">
      <Navbar />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/features/contract" element={<ProtectedRoute><ContractUnderstanding /></ProtectedRoute>} />
        <Route path="/features/workflow" element={<ProtectedRoute><WorkflowGuidance /></ProtectedRoute>} />
        <Route path="/features/dispute" element={<ProtectedRoute><DisputeResolution /></ProtectedRoute>} />
        <Route path="/officer" element={<OfficerRoute><OfficerDashboard /></OfficerRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}