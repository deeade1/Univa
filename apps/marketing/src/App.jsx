import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';

import Navbar from './components/layout/Navbar';
import Footer from './components/layout/Footer';
import Hero from './components/home/Hero';
import ServiceGrid from './components/home/ServiceGrid';
import Ecosystem from './components/home/Ecosystem';

import './App.css';

const About = lazy(() => import('./pages/About'));
const Contact = lazy(() => import('./pages/Contact'));
const Privacy = lazy(() => import('./pages/Privacy'));
const Terms = lazy(() => import('./pages/Terms'));
const ServicePage = lazy(() => import('./pages/ServicePage'));

function Home() {
  return (
    <>
      <Hero />
      <ServiceGrid />
      <Ecosystem />
    </>
  );
}

function PageLoading() {
  return (
    <div className="page-loading" role="status" aria-live="polite">
      <span className="page-loading-spinner" />
      <p>Loading Univa...</p>
    </div>
  );
}

function NotFound() {
  return (
    <main className="not-found container">
      <span className="section-eyebrow">PAGE NOT FOUND</span>
      <h1>Let's get you back on track.</h1>
      <p>The page you're looking for isn't available yet.</p>
      <Link className="button button-primary" to="/">
        Return home
      </Link>
    </main>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div id="top" className="app-shell">
        <Navbar />

        <Suspense fallback={<PageLoading />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/about" element={<About />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/:slug" element={<ServicePage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>

        <Footer />
      </div>
    </BrowserRouter>
  );
}
