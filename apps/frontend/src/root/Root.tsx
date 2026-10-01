import React, { useEffect, useState, Suspense, lazy } from "react";
import { Outlet } from "react-router-dom";
import Loader from "@/components/Loader";
// @ts-expect-error authContext.jsx has no TypeScript declaration file.
import { AuthProvider } from "@/context/authContext";
// Styles
import "@/assets/scss/main.scss";
import "@/assets/index.css";
import { useSettings } from "@/store/settings/SettingsContext";
import { initialState } from "@/store/settings/state";
import whatsappIcon from "@/assets/images/whatsappIcon.png";

// Lazy loaded layouts
const MarketingLayout = lazy(() => import("@/layouts/landing-modules/MarketingLayout"));

const Root: React.FC = () => {
  const { state: settingsState } = useSettings();
  const settings = settingsState?.setting || initialState.setting;

  const [loading, setLoading] = useState(true);

  // Body class — web is marketing-only
  useEffect(() => {
    document.body.classList.add("landing-pages");
    document.body.classList.add("page-transition");
    const t = setTimeout(() => document.body.classList.remove("page-transition"), 300);
    return () => clearTimeout(t);
  }, []);

  // Back to top + scroll
  useEffect(() => {
    const scrollToTop = () =>
      window.scrollTo({ top: 0, behavior: "smooth" as ScrollBehavior });

    const handleScroll = () => {
      const backButton = document.querySelector(".back-to-top");
      if (!backButton) return;
      if (window.scrollY > 200) backButton.classList.add("show");
      else backButton.classList.remove("show");
    };

    const backButton = document.querySelector(".back-to-top");
    backButton?.addEventListener("click", scrollToTop);
    window.addEventListener("scroll", handleScroll);

    return () => {
      backButton?.removeEventListener("click", scrollToTop);
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  // Fake loading — replace with real data fetch later
  useEffect(() => {
    const loadAppData = async () => {
      try {
        await new Promise(resolve => setTimeout(resolve, 800));
      } catch (error) {
        console.error("Error loading app data:", error);
      } finally {
        setLoading(false);
      }
    };
    loadAppData();
  }, []);

  return (
    <AuthProvider>
      <Loader show={loading} />

      {!loading && (
        <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Loading layout...</div>}>
          <MarketingLayout>
            <Suspense fallback={<div>Loading page...</div>}>
              <Outlet />
            </Suspense>
          </MarketingLayout>
        </Suspense>
      )}

      {/* WhatsApp Chat Button */}
      <div className={`chatbot ${!loading ? "show" : ""}`}>
        <div className="animated no-animation ccw-no-hover-an">
          <a
            target="_blank"
            href="https://web.whatsapp.com/send?phone=2348100531161&text="
            rel="noreferrer"
            aria-label="Chat on WhatsApp"
          >
            <img
              className="analytics"
              id="style-9"
              src={whatsappIcon}
              alt="Chat with us on WhatsApp"
              loading="lazy"
              decoding="async"
            />
          </a>
        </div>
      </div>

      {/* Back to Top */}
      <div className="drawer-canvas">
        <a
          href="#main-container"
          className="back-to-top"
          data-shape="circle"
          data-alignment="left"
          title="Go to top"
          aria-label="Go to top"
        >
          <svg className="icon" width="15" height="15" viewBox="0 0 20 20" aria-hidden="true">
            <path d="M10,0L9.4,0.6L0.8,9.1l1.2,1.2l7.1-7.1V20h1.7V3.3l7.1,7.1l1.2-1.2l-8.5-8.5L10,0z" />
          </svg>
        </a>
      </div>
    </AuthProvider>
  );
};

export default Root;