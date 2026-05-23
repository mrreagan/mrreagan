import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";

import "@/App.css";

import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { CartProvider } from "./contexts/CartContext";
import Layout from "./components/Layout";

import Home from "./pages/Home";
import About from "./pages/About";
import Mission from "./pages/Mission";
import Governance from "./pages/Governance";
import Education from "./pages/Education";
import Contact from "./pages/Contact";
import Workshops from "./pages/Workshops";
import WorkshopDetail from "./pages/WorkshopDetail";
import Shop from "./pages/Shop";
import ProductDetail from "./pages/ProductDetail";
import Cart from "./pages/Cart";
import CheckoutSuccess from "./pages/CheckoutSuccess";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Dashboard from "./pages/Dashboard";
import WorkshopHub from "./pages/WorkshopHub";
import Sponsorship from "./pages/Sponsorship";
import Facilitators from "./pages/Facilitators";
import FacilitatorProfile from "./pages/FacilitatorProfile";
import FacilitatorDashboard from "./pages/FacilitatorDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import AdminProducts from "./pages/AdminProducts";
import AdminWorkshops from "./pages/AdminWorkshops";
import PhotoModeration from "./pages/PhotoModeration";
import ReviewsBrowser from "./pages/ReviewsBrowser";
import GovernanceProposals from "./pages/GovernanceProposals";
import IndemnificationPage from "./pages/IndemnificationPage";
import AdminGovernance from "./pages/AdminGovernance";
import PartnersDirectory from "./pages/PartnersDirectory";
import PartnerProfilePage from "./pages/PartnerProfilePage";
import PartnerApply from "./pages/PartnerApply";
import PartnerDashboard from "./pages/PartnerDashboard";
import AdminPartners from "./pages/AdminPartners";
import Profile from "./pages/Profile";

function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="container-page py-20">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/dashboard" replace />;
  return children;
}

const FACILITATOR_ROLES = ["facilitator", "admin"];
const ADMIN_ROLES = ["admin"];

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/about" element={<About />} />
      <Route path="/mission" element={<Mission />} />
      <Route path="/governance" element={<Governance />} />
      <Route path="/education" element={<Education />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/workshops" element={<Workshops />} />
      <Route path="/workshops/:slug" element={<WorkshopDetail />} />
      <Route path="/shop" element={<Shop />} />
      <Route path="/shop/:id" element={<ProductDetail />} />
      <Route path="/cart" element={<Cart />} />
      <Route path="/checkout/success" element={<CheckoutSuccess />} />
      <Route path="/sponsorship" element={<Sponsorship />} />
      <Route path="/facilitators" element={<Facilitators />} />
      <Route path="/facilitators/:slug" element={<FacilitatorProfile />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/reviews" element={<ReviewsBrowser />} />
      <Route path="/governance/proposals" element={<GovernanceProposals />} />
      <Route path="/legal/indemnification" element={<IndemnificationPage />} />
      <Route path="/partners" element={<PartnersDirectory />} />
      <Route path="/partners/apply" element={<PartnerApply />} />
      <Route path="/partners/:slug" element={<PartnerProfilePage />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/workshops/:id"
        element={
          <ProtectedRoute>
            <WorkshopHub />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/partner"
        element={
          <ProtectedRoute>
            <PartnerDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/facilitator"
        element={
          <ProtectedRoute roles={FACILITATOR_ROLES}>
            <FacilitatorDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/products"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminProducts />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/workshops"
        element={
          <ProtectedRoute roles={FACILITATOR_ROLES}>
            <AdminWorkshops />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/photos"
        element={
          <ProtectedRoute roles={FACILITATOR_ROLES}>
            <PhotoModeration />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/governance"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminGovernance />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/partners"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminPartners />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <CartProvider>
            <Toaster position="top-right" richColors closeButton />
            <Layout>
              <AppRoutes />
            </Layout>
          </CartProvider>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
