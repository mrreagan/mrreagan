import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useParams } from "react-router-dom";
import { Toaster } from "sonner";

import "@/App.css";

import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { CartProvider } from "./contexts/CartContext";
import Layout from "./components/Layout";
import { captureInboundVia } from "./lib/shareUtils";

import Home from "./pages/Home";
import About from "./pages/About";
import Mission from "./pages/Mission";
import Governance from "./pages/Governance";
import Education from "./pages/Education"; // eslint-disable-line no-unused-vars -- legacy import kept for emergency restore
import Contact from "./pages/Contact";
import HelpPage from "./pages/HelpPage";
import FounderCollectionPage from "./pages/FounderCollectionPage";
import AdminFounderCarousel from "./pages/AdminFounderCarousel";
import AdminSystem from "./pages/AdminSystem";
import Workshops from "./pages/Workshops"; // eslint-disable-line no-unused-vars -- legacy import kept for emergency restore
import WorkshopDetail from "./pages/WorkshopDetail";
import Experiences from "./pages/Experiences";
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
import AdminHub from "./pages/AdminHub";
import AdminUsers from "./pages/AdminUsers";
import AdminProducts from "./pages/AdminProducts";
import AdminImageQueue from "./pages/AdminImageQueue";
import AdminLegalDocs from "./pages/AdminLegalDocs";
import AdminCampaigns from "./pages/AdminCampaigns";
import CounselReviewChecklist from "./pages/CounselReviewChecklist";
import CounselActivityLog from "./pages/CounselActivityLog";
import MyActivity from "./pages/MyActivity";
import AdminUserActivity from "./pages/AdminUserActivity";
import Campaigns from "./pages/Campaigns";
import CampaignDetail from "./pages/CampaignDetail";
import AdminStudio from "./pages/AdminStudio";
import AdminStudioQueue from "./pages/AdminStudioQueue";
import AdminLuluOps from "./pages/AdminLuluOps";
import AdminEmailOps from "./pages/AdminEmailOps";
import GatherLanding from "./pages/GatherLanding";
import GatherCommunity from "./pages/GatherCommunity";
import GatherPropose from "./pages/GatherPropose";
import GalleryLanding from "./pages/GalleryLanding";
import GalleryArtist from "./pages/GalleryArtist";
import FeaturedInvite from "./pages/FeaturedInvite";
import AdminGalleryProspects from "./pages/AdminGalleryProspects";
import PartnerInvite from "./pages/PartnerInvite";
import PartnerTypeTry from "./pages/PartnerTypeTry";
import AdminPartnerProspects from "./pages/AdminPartnerProspects";
import ArtistStudio from "./pages/ArtistStudio";
import PartnerTypes from "./pages/PartnerTypes";
import VendorStudio from "./pages/VendorStudio";
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
import PartnerSubscribe from "./pages/PartnerSubscribe";
import AdminPartners from "./pages/AdminPartners";
import AdminPayouts from "./pages/AdminPayouts";
import AdminSubscriptions from "./pages/AdminSubscriptions";
import AdminReports from "./pages/AdminReports";
import MyReports from "./pages/MyReports";
import VendorProducts from "./pages/VendorProducts";
import AdminVendorProducts from "./pages/AdminVendorProducts";
import JoinUs from "./pages/JoinUs";
import JoinUsRole from "./pages/JoinUsRole";
import AdminFoundationRoles from "./pages/AdminFoundationRoles";
import AdminFoundationApplications from "./pages/AdminFoundationApplications";
import PartnerSalesReports from "./pages/PartnerSalesReports";
import AdminPartnerSalesReports from "./pages/AdminPartnerSalesReports";
import PartnerFeatured from "./pages/PartnerFeatured";
import AdminFeatured from "./pages/AdminFeatured";
import Research from "./pages/Research";
import PartnerResearch from "./pages/PartnerResearch";
import PartnerPayouts from "./pages/PartnerPayouts";
import Profile from "./pages/Profile";
import Bookmarks from "./pages/Bookmarks";
import Messages, { MessageThread } from "./pages/Messages";
import MyDisputes from "./pages/MyDisputes";
import DisputeDetail from "./pages/DisputeDetail";
import OmbudsmanQueue from "./pages/OmbudsmanQueue";
import AdminRefunds from "./pages/AdminRefunds";
import AgreementPage from "./pages/AgreementPage";
import AdminResearch from "./pages/AdminResearch";
import AiWallet from "./pages/AiWallet";
import AdminAiUsage from "./pages/AdminAiUsage";
import AdminAgreements from "./pages/AdminAgreements";
import EngravingGallery from "./pages/EngravingGallery";
import FbPromoGallery from "./pages/FbPromoGallery";
import MarketingIndex from "./pages/MarketingIndex";
import ArtistPartnershipTerms from "./pages/ArtistPartnershipTerms";
import OffSiteReport from "./pages/OffSiteReport";
import PayoutMethod from "./pages/PayoutMethod";
import PatchesLanding from "./pages/PatchesLanding";
import AdminArtistPayouts from "./pages/AdminArtistPayouts";
import AiOverview from "./pages/AiOverview";
import Connect from "./pages/Connect";
import ScrollToTop from "./components/ScrollToTop";

function ProtectedRoute({ children, roles, allowOmbudsman }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="container-page py-20">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) {
    if (allowOmbudsman && user.is_ombudsman) return children;
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

const FACILITATOR_ROLES = ["facilitator", "admin"];
const ADMIN_ROLES = ["admin", "readonly_admin"];

// Slug-preserving redirects from old canonical paths to new canonical paths.
// react-router's <Navigate> doesn't templatize :params, so we read the param
// via useParams and build the destination URL ourselves. The 'replace' prop
// keeps the old URL out of browser history.
const SlugRedirect = ({ to }) => {
  const params = useParams();
  const dest = Object.keys(params).reduce(
    (acc, key) => acc.replace(`:${key}`, params[key]),
    to
  );
  return <Navigate to={dest} replace />;
};

const WorkshopRedirect  = () => <SlugRedirect to="/practice/:slug" />;
const ShopRedirect      = () => <SlugRedirect to="/equip/:id" />;
const PartnerRedirect   = () => <SlugRedirect to="/partner/:slug" />;
const JoinUsRedirect    = () => <SlugRedirect to="/join/:slug" />;

function AppRoutes() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<Home />} />
      <Route path="/about" element={<About />} />
      <Route path="/ai" element={<AiOverview />} />
      <Route path="/mission" element={<Mission />} />

      {/* Lead — canonical path is /lead. /governance preserved as redirect. */}
      <Route path="/lead" element={<Governance />} />
      <Route path="/lead/proposals" element={<GovernanceProposals />} />
      <Route path="/governance" element={<Navigate to="/lead" replace />} />
      <Route path="/governance/proposals" element={<Navigate to="/lead/proposals" replace />} />

      <Route path="/contact" element={<Contact />} />
      <Route path="/help" element={<HelpPage />} />
      <Route path="/equip/collection/founder" element={<FounderCollectionPage />} />
      <Route path="/admin/founder-carousel" element={<AdminFounderCarousel />} />
      <Route path="/admin/system" element={<AdminSystem />} />

      {/* Practice — canonical path is /practice. /experiences and /workshops preserved as redirects. */}
      <Route path="/practice" element={<Experiences />} />
      <Route path="/practice/:slug" element={<WorkshopDetail />} />
      <Route path="/experiences" element={<Navigate to="/practice" replace />} />
      <Route path="/education" element={<Navigate to="/practice" replace />} />
      <Route path="/workshops" element={<Navigate to="/practice" replace />} />
      <Route path="/workshops/:slug" element={<WorkshopRedirect />} />

      {/* Equip — canonical path is /equip. /shop preserved as redirect. */}
      <Route path="/equip" element={<Shop />} />
      <Route path="/equip/:id" element={<ProductDetail />} />
      <Route path="/shop" element={<Navigate to="/equip" replace />} />
      <Route path="/shop/:id" element={<ShopRedirect />} />

      <Route path="/cart" element={<Cart />} />
      <Route path="/checkout/success" element={<CheckoutSuccess />} />

      {/* Sponsor — canonical /sponsor. /sponsorship preserved as redirect. */}
      <Route path="/sponsor" element={<Sponsorship />} />
      <Route path="/sponsorship" element={<Navigate to="/sponsor" replace />} />

      {/* Sponsor campaigns — targeted drives (pledge-only, not tax-deductible) */}
      <Route path="/campaigns" element={<Campaigns />} />
      <Route path="/campaigns/:slug" element={<CampaignDetail />} />

      <Route path="/facilitators" element={<Facilitators />} />
      <Route path="/facilitators/:slug" element={<FacilitatorProfile />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/reviews" element={<ReviewsBrowser />} />
      <Route path="/legal/indemnification" element={<IndemnificationPage />} />

      {/* Partner — canonical /partner. /partners preserved as redirect. */}
      <Route path="/partner" element={<PartnersDirectory />} />
      <Route path="/partner/types" element={<PartnerTypes />} />
      <Route path="/partner/types/:type/try" element={<PartnerTypeTry />} />
      <Route path="/partner/invite/:token" element={<PartnerInvite />} />
      <Route path="/partner/apply" element={<PartnerApply />} />
      <Route path="/partner/subscribe" element={<PartnerSubscribe />} />
      <Route path="/partner/:slug" element={<PartnerProfilePage />} />
      <Route path="/partners" element={<Navigate to="/partner" replace />} />
      <Route path="/partners/apply" element={<Navigate to="/partner/apply" replace />} />
      <Route path="/partners/subscribe" element={<Navigate to="/partner/subscribe" replace />} />
      <Route path="/partners/:slug" element={<PartnerRedirect />} />

      {/* Gather — communities by geography */}
      <Route path="/gather" element={<GatherLanding />} />
      <Route path="/gather/propose" element={<GatherPropose />} />
      <Route path="/gather/community/*" element={<GatherCommunity />} />

      {/* Gallery — artist exhibition + sales */}
      <Route path="/gallery" element={<GalleryLanding />} />
      <Route path="/gallery/invite/:token" element={<FeaturedInvite />} />
      <Route path="/gallery/:slug" element={<GalleryArtist />} />
      <Route
        path="/gallery/me/studio"
        element={<ProtectedRoute><ArtistStudio /></ProtectedRoute>}
      />

      {/* Join — canonical /join. /join-us preserved as redirect. */}
      <Route path="/join" element={<JoinUs />} />
      <Route path="/join/:slug" element={<JoinUsRole />} />
      <Route path="/join-us" element={<Navigate to="/join" replace />} />
      <Route path="/join-us/:slug" element={<JoinUsRedirect />} />

      <Route path="/featured" element={<Navigate to="/partner" replace />} />
      <Route path="/research" element={<Research />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      <Route path="/connect" element={<Connect />} />

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
        path="/dashboard/reports"
        element={
          <ProtectedRoute>
            <MyReports />
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
            <AdminHub />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/stats"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminUsers />
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
        path="/admin/image-queue"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminImageQueue />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/legal-docs"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminLegalDocs />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/campaigns"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminCampaigns />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/counsel-review"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <CounselReviewChecklist />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/counsel-activity"
        element={
          <ProtectedRoute roles={["admin"]}>
            <CounselActivityLog />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/user-activity"
        element={
          <ProtectedRoute roles={["admin"]}>
            <AdminUserActivity />
          </ProtectedRoute>
        }
      />
      <Route
        path="/account/activity"
        element={
          <ProtectedRoute>
            <MyActivity />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/studio"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminStudio />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/studio/queue"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminStudioQueue />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/lulu-ops"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminLuluOps />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/email-ops"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminEmailOps />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/vendor/studio"
        element={
          <ProtectedRoute>
            <VendorStudio />
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
      <Route
        path="/admin/payouts"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminPayouts />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/subscriptions"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminSubscriptions />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/reports"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminReports />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/vendor/products"
        element={
          <ProtectedRoute>
            <VendorProducts />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/vendor-products"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminVendorProducts />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/partner/sales-reports"
        element={
          <ProtectedRoute>
            <PartnerSalesReports />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/partner/featured"
        element={
          <ProtectedRoute>
            <PartnerFeatured />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/partner/research"
        element={
          <ProtectedRoute>
            <PartnerResearch />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/partner/payouts"
        element={
          <ProtectedRoute>
            <PartnerPayouts />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/partner-sales-reports"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminPartnerSalesReports />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/featured"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminFeatured />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/gallery/prospects"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminGalleryProspects />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/partners/prospects"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminPartnerProspects />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/foundation-roles"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminFoundationRoles />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/foundation-applications"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminFoundationApplications />
          </ProtectedRoute>
        }
      />

      <Route
        path="/dashboard/bookmarks"
        element={
          <ProtectedRoute>
            <Bookmarks />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/messages"
        element={
          <ProtectedRoute>
            <Messages />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/messages/:thread_id"
        element={
          <ProtectedRoute>
            <MessageThread />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/disputes"
        element={
          <ProtectedRoute>
            <MyDisputes />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/disputes/:dispute_id"
        element={
          <ProtectedRoute>
            <DisputeDetail adminMode={false} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/ombudsman"
        element={
          <ProtectedRoute roles={ADMIN_ROLES} allowOmbudsman>
            <OmbudsmanQueue />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/disputes/:dispute_id"
        element={
          <ProtectedRoute roles={ADMIN_ROLES} allowOmbudsman>
            <DisputeDetail adminMode={true} />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/refunds"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminRefunds />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/research"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminResearch />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/ai-usage"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminAiUsage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/legal/agreements"
        element={
          <ProtectedRoute roles={ADMIN_ROLES}>
            <AdminAgreements />
          </ProtectedRoute>
        }
      />
      <Route path="/engraving" element={<EngravingGallery />} />
      <Route path="/fb-promo" element={<FbPromoGallery />} />
      <Route path="/marketing" element={<MarketingIndex />} />
      <Route path="/partner/artist" element={<ArtistPartnershipTerms />} />
      <Route path="/partner/me/off-site-report" element={<OffSiteReport />} />
      <Route path="/partner/me/payout-method" element={<PayoutMethod />} />
      <Route path="/shop/patches" element={<PatchesLanding />} />
      <Route path="/patches" element={<PatchesLanding />} />
      <Route path="/admin/artist/payouts" element={<AdminArtistPayouts />} />
      <Route
        path="/dashboard/ai-wallet"
        element={
          <ProtectedRoute>
            <AiWallet />
          </ProtectedRoute>
        }
      />
      <Route
        path="/legal/agreement"
        element={
          <ProtectedRoute>
            <AgreementPage />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

function App() {
  React.useEffect(() => { captureInboundVia(); }, []);
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
