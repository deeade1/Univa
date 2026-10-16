import { Link } from 'react-router-dom';

const LAST_UPDATED = 'October 12, 2026';

export default function Privacy() {
  return (
    <main className="legal-page container">
      <header className="legal-page-header">
        <span className="section-eyebrow">PRIVACY AT UNIVA</span>
        <h1>Privacy Policy</h1>
        <p>
          This policy concerns the public Univa marketing website.
          It explains the information-handling boundaries of this
          website and distinguishes it from the wider Univa platform.
        </p>
        <p className="legal-updated">
          Last updated: {LAST_UPDATED}
        </p>
      </header>

      <div className="legal-content">
        <section>
          <h2>1. Scope of this policy</h2>
          <p>
            This policy applies to your use of the public Univa
            marketing website, including its informational pages and
            links to other pages on this website.
          </p>
          <p>
            The wider Univa platform may offer separate services,
            including commerce, transport, banking-related features,
            and real estate. Those services may process information
            under different systems and service-specific terms or
            privacy notices. This website policy should not be treated
            as a complete description of those services.
          </p>
        </section>

        <section>
          <h2>2. Information you provide on this website</h2>
          <p>
            You may contact Univa using the contact details published
            on this website, including the general address
            {' '}
            <a href="mailto:support@univa.app">
              support@univa.app
            </a>.
            If you send an email, the information you include in that
            email will be processed by the email services involved
            in sending and receiving it.
          </p>
          <p>
            The contact form currently displayed on this marketing
            website performs browser-side validation only. It is not
            connected to a Univa backend that receives or stores
            submissions. Clicking its submit control does not send
            your message to Univa.
          </p>
          <p>
            Do not use that form to send confidential, financial,
            identity, health, or other sensitive information. Use
            the published email address for general enquiries.
          </p>
        </section>

        <section>
          <h2>3. Technical information</h2>
          <p>
            When a browser requests a website, the website's hosting
            and delivery infrastructure may process technical request
            information, such as an IP address, requested URL,
            timestamp, browser details, and security-related events.
            Whether and for how long this information is logged depends
            on the production hosting configuration and its providers.
          </p>
          <p>
            Univa must verify its actual hosting and logging
            configuration before making more specific statements
            about what is collected, who can access it, or how long
            it is retained.
          </p>
        </section>

        <section>
          <h2>4. Cookies, local storage, and analytics</h2>
          <p>
            This policy does not claim that the marketing website uses
            advertising cookies, analytics, or tracking technologies.
            Those technologies and the website's use of browser storage
            must be verified against the deployed code and third-party
            integrations.
          </p>
          <p>
            If non-essential cookies, analytics, embedded services,
            or similar technologies are introduced, this notice and
            any required choice or consent controls should be updated
            before those technologies are used.
          </p>
        </section>

        <section>
          <h2>5. How information may be used</h2>
          <p>
            Information processed in connection with this website
            should be used only for identified and lawful purposes,
            such as delivering requested pages, protecting the
            website, diagnosing technical problems, or responding
            to communications that Univa actually receives.
          </p>
          <p>
            The current contact form does not deliver submissions
            to Univa. We therefore do not represent that enquiries
            submitted through that form are received, reviewed,
            or retained by our team.
          </p>
        </section>

        <section>
          <h2>6. Service providers and external links</h2>
          <p>
            Website hosting, email delivery, security, and other
            technical providers may process information when their
            services are used. The providers involved and any
            international transfers must be confirmed from the
            production configuration and applicable contracts.
          </p>
          <p>
            Links to external websites are provided for convenience.
            A third-party website operates under its own privacy
            practices and terms. Review those notices before
            providing information to that website.
          </p>
        </section>

        <section>
          <h2>7. Retention and security</h2>
          <p>
            Retention depends on the type of information, the purpose
            for which it is processed, applicable legal requirements,
            and the systems that hold it. The marketing website's
            actual hosting-log retention and email-retention practices
            must be confirmed before specific periods can be stated.
          </p>
          <p>
            Appropriate technical and organisational safeguards
            should be maintained for personal information processed
            in connection with the website. This notice is not a
            guarantee that any system is free from security risk.
          </p>
        </section>

        <section>
          <h2>8. Your privacy rights</h2>
          <p>
            Depending on applicable law and the circumstances of
            the processing, you may have rights to request access
            to personal information, correction, deletion, restriction
            of processing, objection, or data portability, and to
            withdraw consent where consent is the applicable basis.
          </p>
          <p>
            To raise a privacy question or request, contact
            {' '}
            <a href="mailto:support@univa.app?subject=Privacy%20request">
              support@univa.app
            </a>
            {' '}
            and include “Privacy request” in the subject. Do not
            include passwords, payment credentials, or identity
            documents in an initial email. We may need to verify
            your identity appropriately before acting on a request.
          </p>
          <p>
            The responsible legal entity and any dedicated privacy
            contact should be added here once confirmed.
          </p>
        </section>

        <section>
          <h2>9. Children</h2>
          <p>
            This marketing website is not intended to collect
            personal information through its contact form, which
            does not transmit submissions. Age requirements for
            individual Univa services are governed by the rules
            applicable to those services and should be reviewed
            separately.
          </p>
        </section>

        <section>
          <h2>10. Changes to this policy</h2>
          <p>
            This policy should be updated when the website's actual
            information practices materially change. The date above
            identifies the date of this version; it is not a promise
            that every change will be individually notified.
          </p>
        </section>

        <section>
          <h2>11. Contact</h2>
          <p>
            For general enquiries or privacy questions, email
            {' '}
            <a href="mailto:support@univa.app">
              support@univa.app
            </a>.
          </p>
          <p>
            Univa's full legal entity name and registered contact
            details should be published here once confirmed.
          </p>
        </section>
      </div>

      <div className="legal-page-footer">
        <Link to="/">Back to home</Link>
        <Link to="/terms">Read Terms of Service</Link>
        <Link to="/contact">Contact</Link>
      </div>
    </main>
  );
}
