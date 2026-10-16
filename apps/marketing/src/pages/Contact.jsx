
import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Mail,
  MessageCircle,
  Handshake,
  BriefcaseBusiness,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';

const initialForm = {
  name: '',
  email: '',
  topic: 'General enquiry',
  message: '',
};

const enquiryTypes = [
  'General enquiry',
  'Business enquiry',
  'Partnership',
  'Product information',
  'Other',
];

export default function Contact() {
  const [form, setForm] = useState(initialForm);
  const [validationMessage, setValidationMessage] = useState('');

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));

    setValidationMessage('');
  }

  function handleSubmit(event) {
    event.preventDefault();

    setValidationMessage(
      'Your form passed browser validation, but no message was sent. The contact form still needs to be connected to the Univa backend.'
    );
  }

  return (
    <main className="contact-page">
      <section className="contact-hero">
        <div className="container contact-hero-layout">
          <div className="contact-intro">
            <span className="about-eyebrow">CONTACT UNIVA</span>
            <h1>
              Let's start
              <span> a conversation.</span>
            </h1>
            <p>
              Have a question about Univa, a business proposal, or a potential
              partnership? Tell us what you have in mind.
            </p>

            <div className="contact-points">
              <div className="contact-point">
                <span className="contact-point-icon">
                  <Handshake size={21} />
                </span>
                <span>
                  <strong>Partnerships</strong>
                  <small>Discuss collaboration and business opportunities.</small>
                </span>
              </div>

              <div className="contact-point">
                <span className="contact-point-icon">
                  <BriefcaseBusiness size={21} />
                </span>
                <span>
                  <strong>Business enquiries</strong>
                  <small>Ask about the platform and its service areas.</small>
                </span>
              </div>

              <div className="contact-point">
                <span className="contact-point-icon">
                  <MessageCircle size={21} />
                </span>
                <span>
                  <strong>General questions</strong>
                  <small>Share your questions or feedback with the team.</small>
                </span>
              </div>
            </div>
          </div>

          <div className="contact-form-card">
            <div className="contact-form-heading">
              <span className="contact-form-icon">
                <Mail size={23} />
              </span>
              <div>
                <h2>Send an enquiry</h2>
                <p>Fill in the details below.</p>
              </div>
            </div>

            <form className="contact-form" onSubmit={handleSubmit}>
              <div className="contact-field">
                <label htmlFor="contact-name">Full name</label>
                <input
                  id="contact-name"
                  name="name"
                  type="text"
                  autoComplete="name"
                  placeholder="Your name"
                  value={form.name}
                  onChange={handleChange}
                  required
                  maxLength={120}
                />
              </div>

              <div className="contact-field">
                <label htmlFor="contact-email">Email address</label>
                <input
                  id="contact-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={handleChange}
                  required
                  maxLength={254}
                />
              </div>

              <div className="contact-field">
                <label htmlFor="contact-topic">What would you like to discuss?</label>
                <select
                  id="contact-topic"
                  name="topic"
                  value={form.topic}
                  onChange={handleChange}
                  required
                >
                  {enquiryTypes.map((type) => (
                    <option value={type} key={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>

              <div className="contact-field">
                <label htmlFor="contact-message">Message</label>
                <textarea
                  id="contact-message"
                  name="message"
                  placeholder="Tell us a little about your enquiry..."
                  value={form.message}
                  onChange={handleChange}
                  required
                  minLength={10}
                  maxLength={5000}
                  rows={5}
                />
                <span className="contact-character-count">
                  {form.message.length}/5000 characters
                </span>
              </div>

              <button
                type="submit"
                className="button button-primary contact-submit"
              >
                Validate enquiry <ArrowRight size={18} />
              </button>

              {validationMessage && (
                <div className="contact-form-notice" role="status">
                  <AlertCircle size={19} />
                  <p>{validationMessage}</p>
                </div>
              )}

              <p className="contact-form-disclaimer">
                This is a frontend demonstration. Your information is not
                transmitted or stored by this form.
              </p>
            </form>
          </div>
        </div>
      </section>

      <section className="contact-alternative">
        <div className="container contact-alternative-inner">
          <span className="contact-alternative-icon">
            <CheckCircle2 size={21} />
          </span>
          <div>
            <h2>Looking to explore Univa first?</h2>
            <p>Visit the homepage to discover our service areas.</p>
          </div>
          <Link to="/" className="contact-alternative-link">
            Explore Univa <ArrowRight size={17} />
          </Link>
        </div>
      </section>
    </main>
  );
}
