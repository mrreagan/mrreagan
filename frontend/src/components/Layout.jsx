import React, { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { BrandLogo } from "./BrandLogo";
import { useAuth } from "../contexts/AuthContext";
import { useCart } from "../contexts/CartContext";
import { ShoppingBag, Menu, X, User, LogOut, ChevronDown } from "lucide-react";
import AgreementResignBanner from "./AgreementResignBanner";
import AssistantWidget from "./AssistantWidget";

const NAV_EXPLORE = [
  { to: "/experiences", label: "Practice" },
  { to: "/shop",        label: "Equip" },
  { to: "/research",    label: "Research" },
  { to: "/partners",    label: "Partner" },
  { to: "/sponsorship", label: "Sponsor" },
  { to: "/governance",  label: "Lead" },
  { to: "/join-us",     label: "Join" },
  { to: "/connect",     label: "Connect" },
];

const NAV_FOUNDATION = [
  { to: "/about",   label: "About" },
  { to: "/mission", label: "Mission" },
];

// Flattened list still used by the desktop top bar so the existing
// horizontal nav layout doesn't shift mid-session. Desktop shows only
// the primary 8 verbs; About/Mission live in the mobile drawer + footer.
const NAV = [...NAV_EXPLORE];

// ---------- Cart icon button ----------
function CartButton({ count }) {
  return (
    <Link
      to="/cart"
      className="relative p-2 rounded-full hover:bg-[#E5E1D8]/40 transition"
      data-testid="cart-link"
      aria-label="Cart"
    >
      <ShoppingBag size={20} strokeWidth={1.5} className="text-[#1A2424]" />
      {count > 0 && (
        <span
          className="absolute -top-0.5 -right-0.5 bg-[#C9A961] text-white text-[10px] font-medium rounded-full h-4 min-w-4 px-1 flex items-center justify-center"
          data-testid="cart-count"
        >
          {count}
        </span>
      )}
    </Link>
  );
}

// ---------- Desktop nav links ----------
function DesktopNav() {
  return (
    <nav className="hidden xl:flex items-center gap-0.5" data-testid="header-nav">
      {NAV.map((n) => (
        <NavLink
          key={n.to}
          to={n.to}
          className={({ isActive }) =>
            `px-2 py-2 text-[13px] font-medium transition-colors hover:text-[#476B6B] ${
              isActive ? "text-[#476B6B]" : "text-[#1A2424]"
            }`
          }
          data-testid={`nav-${n.to.slice(1)}`}
        >
          {n.label}
        </NavLink>
      ))}
    </nav>
  );
}

// ---------- User dropdown menu ----------
function UserMenu({ user, onLogout }) {
  const [open, setOpen] = useState(false);
  const handleLogout = async () => {
    await onLogout();
    setOpen(false);
  };
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-3 py-2 rounded-full hover:bg-[#E5E1D8]/40 transition text-sm font-medium"
        data-testid="user-menu-trigger"
      >
        <User size={18} strokeWidth={1.5} />
        <span className="hidden sm:inline">{user.first_name}</span>
        <ChevronDown size={14} strokeWidth={1.5} />
      </button>
      {open && (
        <div
          className="absolute right-0 mt-2 w-56 bg-white border border-[#E5E1D8] rounded-xl shadow-lg overflow-hidden"
          data-testid="user-menu-dropdown"
        >
          <Link to="/dashboard" onClick={() => setOpen(false)} className="block px-4 py-3 text-sm hover:bg-[#FAF8F5]" data-testid="menu-dashboard">
            My Dashboard
          </Link>
          <Link to="/dashboard/messages" onClick={() => setOpen(false)} className="block px-4 py-3 text-sm hover:bg-[#FAF8F5]" data-testid="menu-messages">
            Messages
          </Link>
          <Link to="/dashboard/bookmarks" onClick={() => setOpen(false)} className="block px-4 py-3 text-sm hover:bg-[#FAF8F5]" data-testid="menu-bookmarks">
            My Bookmarks
          </Link>
          <Link to="/dashboard/disputes" onClick={() => setOpen(false)} className="block px-4 py-3 text-sm hover:bg-[#FAF8F5]" data-testid="menu-disputes">
            My Disputes
          </Link>
          {user.is_ombudsman && (
            <Link to="/admin/ombudsman" onClick={() => setOpen(false)} className="block px-4 py-3 text-sm hover:bg-[#FAF8F5] text-[#476B6B] font-medium" data-testid="menu-ombudsman">
              Ombudsman queue
            </Link>
          )}
          {user.role === "facilitator" && (
            <Link to="/facilitator" onClick={() => setOpen(false)} className="block px-4 py-3 text-sm hover:bg-[#FAF8F5]" data-testid="menu-facilitator">
              Facilitator Dashboard
            </Link>
          )}
          {user.role === "admin" && (
            <Link to="/admin" onClick={() => setOpen(false)} className="block px-4 py-3 text-sm hover:bg-[#FAF8F5]" data-testid="menu-admin">
              Admin Dashboard
            </Link>
          )}
          <Link to="/profile" onClick={() => setOpen(false)} className="block px-4 py-3 text-sm hover:bg-[#FAF8F5] border-t border-[#E5E1D8]" data-testid="menu-profile">
            Edit Profile
          </Link>
          <Link to="/dashboard/ai-wallet" onClick={() => setOpen(false)} className="block px-4 py-3 text-sm hover:bg-[#FAF8F5] border-t border-[#E5E1D8]" data-testid="menu-ai-wallet">
            AI Wallet
          </Link>
          <button
            onClick={handleLogout}
            className="w-full text-left px-4 py-3 text-sm hover:bg-[#FAF8F5] border-t border-[#E5E1D8] flex items-center gap-2 text-[#9E3C3C]"
            data-testid="menu-logout"
          >
            <LogOut size={14} strokeWidth={1.5} />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

// ---------- Auth buttons (signed-out state) ----------
// "Sign in" is ALWAYS visible (including mobile) so users never have to hunt
// inside the hamburger menu to log in. "Join" stays hidden on the smallest
// screens to preserve room for the brand mark and cart.
function AuthButtons() {
  return (
    <div className="flex items-center gap-1 sm:gap-2">
      <Link
        to="/login"
        className="text-sm font-medium text-[#1A2424] hover:text-[#476B6B] px-2 py-1 whitespace-nowrap"
        data-testid="header-login-link"
      >
        Sign in
      </Link>
      <Link
        to="/register"
        className="btn-primary text-sm hidden sm:inline-flex"
        data-testid="header-register-link"
      >
        Join
      </Link>
    </div>
  );
}

// ---------- Mobile menu drawer ----------
function MobileMenuSection({ heading, items, onClose, testidPrefix }) {
  return (
    <div className="pt-2 first:pt-0" data-testid={`mobile-section-${testidPrefix}`}>
      <p className="label mt-3 mb-1 text-[#C9A961]">{heading}</p>
      {items.map((n) => (
        <Link
          key={n.to}
          to={n.to}
          onClick={onClose}
          className="block py-2.5 text-base text-[#1A2424]"
          data-testid={`mobile-nav-${n.to.slice(1)}`}
        >
          {n.label}
        </Link>
      ))}
    </div>
  );
}

function MobileMenu({ user, onClose }) {
  return (
    <div className="xl:hidden border-t border-[#E5E1D8] bg-white" data-testid="mobile-menu">
      <div className="container-page py-4 flex flex-col">
        <MobileMenuSection heading="Explore"    items={NAV_EXPLORE}    onClose={onClose} testidPrefix="explore" />
        <MobileMenuSection heading="Foundation" items={NAV_FOUNDATION} onClose={onClose} testidPrefix="foundation" />
        {!user && (
          <div className="flex gap-2 pt-5 mt-2 border-t border-[#E5E1D8]">
            <Link to="/login" onClick={onClose} className="btn-outline flex-1 justify-center">
              Sign in
            </Link>
            <Link to="/register" onClick={onClose} className="btn-primary flex-1 justify-center">
              Join
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export function Header() {
  const { user, logout } = useAuth();
  const { count } = useCart();
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <header className="header-blur sticky top-0 z-50" data-testid="site-header">
      <div className="container-page flex items-center justify-between py-4">
        <Link to="/" data-testid="header-logo-link">
          <BrandLogo size="sm" />
        </Link>
        <DesktopNav />
        <div className="flex items-center gap-2">
          <CartButton count={count} />
          {user ? <UserMenu user={user} onLogout={handleLogout} /> : <AuthButtons />}
          <button
            className="xl:hidden p-2"
            onClick={() => setMobileOpen(!mobileOpen)}
            data-testid="mobile-menu-toggle"
            aria-label="Menu"
          >
            {mobileOpen ? <X size={22} strokeWidth={1.5} /> : <Menu size={22} strokeWidth={1.5} />}
          </button>
        </div>
      </div>
      {mobileOpen && <MobileMenu user={user} onClose={() => setMobileOpen(false)} />}
    </header>
  );
}

// ---------- Footer column helper ----------
function FooterColumn({ heading, links }) {
  return (
    <div>
      <p className="label mb-4">{heading}</p>
      <ul className="space-y-2 text-sm">
        {links.map((l) => (
          <li key={l.to}>
            <Link to={l.to} className="text-[#1A2424] hover:text-[#476B6B]">
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

const FOOTER_EXPLORE = [
  { to: "/experiences", label: "Practice" },
  { to: "/shop", label: "Equip" },
  { to: "/research", label: "Research" },
  { to: "/partners", label: "Partner" },
  { to: "/sponsorship", label: "Sponsor" },
  { to: "/governance", label: "Lead" },
  { to: "/join-us", label: "Join" },
  { to: "/connect", label: "Connect" },
];
const FOOTER_FOUNDATION = [
  { to: "/about", label: "About" },
  { to: "/mission", label: "Mission" },
  { to: "/contact", label: "Contact" },
];

export function Footer() {
  return (
    <footer className="border-t border-[#E5E1D8] bg-white mt-20" data-testid="site-footer">
      <div className="container-page py-14 grid grid-cols-1 md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <BrandLogo size="md" showMotto />
          <p className="mt-5 text-sm text-[#5C6B6B] max-w-md leading-relaxed">
            Secure bonds are our birthright. We exist to empower everyone with the tools and support we
            all occasionally need to claim and recover our secure bonds with our precious people. So we
            can all thrive.
          </p>
          <p className="mt-5 text-sm text-[#5C6B6B]">
            2148 W Earll Dr, Phoenix, AZ 85015
            <br />
            <a href="mailto:hello@birthright.live" className="hover:text-[#476B6B]">
              hello@birthright.live
            </a>
          </p>
        </div>
        <FooterColumn heading="Explore" links={FOOTER_EXPLORE} />
        <FooterColumn heading="Foundation" links={FOOTER_FOUNDATION} />
      </div>
      <div className="border-t border-[#E5E1D8]">
        <div className="container-page py-5 text-xs text-[#5C6B6B] flex flex-col sm:flex-row justify-between gap-2">
          <span>© {new Date().getFullYear()} birthright foundation. All rights reserved.</span>
          <span>birthright.live</span>
        </div>
      </div>
    </footer>
  );
}

export default function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <AgreementResignBanner />
      <main className="flex-1" data-testid="main-content">
        {children}
      </main>
      <Footer />
      <AssistantWidget />
    </div>
  );
}
