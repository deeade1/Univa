import { ReactNode } from "react";
import LandingHeader from "@/components/landing-modules/partials/header";
import Footer from "@/components/landing-modules/partials/footer";
import Container from "@/components/Container";

interface MarketingLayoutProps {
  children: ReactNode;
}

const MarketingLayout: React.FC<MarketingLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col bg-white text-gray-900">
      <LandingHeader />
      <main className="flex-grow pt-16">
        <Container>{children}</Container>
      </main>
      <Footer />
    </div>
  );
};

export default MarketingLayout;
