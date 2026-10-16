import { Link } from 'react-router-dom';

const LAST_UPDATED = 'October 12, 2026';

export default function Terms() {
  return (
    <main className="legal-page container">
      <header className="legal-page-header">
        <span className="section-eyebrow">WEBSITE TERMS</span>
        <h1>Terms of Use</h1>
        <p>
          These terms concern access to and use of the public Univa
          marketing website. Additional terms may apply to separate
          Univa products and services.
        </p>
        <p className="legal-updated">
          Last updated: {LAST_UPDATED}
        </p>
      </header>

      <div className="legal-content">
        <section>
          <h2>1. Who these terms cover</h2>
          <p>
            These terms apply to your use of the public Univa marketing
            website, including its informational content, navigation,
            and links to pages within the website.
          </p>
          <p>
            The legal entity responsible for operating this website
            must be identified by its correct registered name before
            these terms are treated as final. “Univa” is used here
            as the platform and brand name, not as a representation
            of a particular registered legal entity.
          </p>
        </section>

        <section>
          <h2>2. Acceptable use</h2>
          <p>
            You may use this website for lawful purposes and in a way
            that does not interfere with its operation or other
            visitors' access.
          </p>
          <p>You must not:</p>
          <ul>
            <li>
              Use the website to engage in unlawful, deceptive,
              or fraudulent activity.
            </li>
            <li>
              Attempt unauthorised access to website systems,
              accounts, or information.
            </li>
            <li>
              Deliberately disrupt the website or introduce
              malicious code.
            </li>
            <li>
              Use automated access in a way that damages, overloads,
              or unreasonably interferes with the website.
            </li>
            <li>
              Misrepresent your identity, authority, or affiliation
              with another person or organisation.
            </li>
          </ul>
        </section>

        <section>
          <h2>3. Website information</h2>
          <p>
            The website provides general information about Univa
            and its intended service areas. Descriptions, features,
            availability, and plans may change as the platform develops.
          </p>
          <p>
            Unless expressly stated in a separate applicable agreement,
            website descriptions are not a binding offer to provide a
            particular service, complete a transaction, or make a
            feature available in a specific location.
          </p>
          <p>
            Do not rely on general marketing content as financial,
            investment, legal, property, transport, or other
            professional advice.
          </p>
        </section>

        <section>
          <h2>4. Separate Univa services</h2>
          <p>
            Univa's wider platform may include commerce, transport,
            banking-related features, real estate, social features,
            and other services. These website terms do not by themselves
            establish the contractual terms for those services.
          </p>
          <p>
            When you use a separate service, its own terms, eligibility
            requirements, privacy notice, fees, transaction rules,
            and other conditions may apply. Read the applicable
            service-specific terms before using that service.
          </p>
          <p>
            References to banking, investments, payments, or other
            regulated activities on this website do not, by themselves,
            represent that a particular service is available, licensed,
            authorised, or offered directly by the website operator.
            The responsible entity and applicable regulatory status
            should be confirmed for each relevant service.
          </p>
        </section>

        <section>
          <h2>5. Intellectual property</h2>
          <p>
            Website text, visual design, branding, graphics, and
            other materials may be protected by intellectual-property
            laws. Rights belong to Univa, the relevant rights holder,
            or the applicable licensor.
          </p>
          <p>
            You may view and use the website for ordinary personal
            or business information purposes. Unless permitted by
            law or authorised by the relevant rights holder, you
            must not reproduce, distribute, adapt, commercially
            exploit, or misrepresent protected materials.
          </p>
          <p>
            Third-party names, marks, and materials remain the
            property of their respective owners.
          </p>
        </section>

        <section>
          <h2>6. Links to third-party websites</h2>
          <p>
            This website may link to websites or services operated
            by other organisations. Those organisations control
            their own content, terms, and privacy practices.
          </p>
          <p>
            A link does not, by itself, mean that Univa endorses
            or controls the third-party service. Use external
            services at your own discretion and review their
            applicable terms.
          </p>
        </section>

        <section>
          <h2>7. Website contact form</h2>
          <p>
            The contact form currently displayed on this marketing
            website is a frontend demonstration. It validates input
            in the browser but does not transmit submissions to
            Univa or store them through a Univa backend.
          </p>
          <p>
            Do not rely on that form to deliver a message, request,
            notice, or complaint. For general enquiries, use
            {' '}
            <a href="mailto:support@univa.app">
              support@univa.app
            </a>.
          </p>
        </section>

        <section>
          <h2>8. Availability and changes</h2>
          <p>
            We may update website content, change features, or
            temporarily restrict access for maintenance, security,
            or operational reasons where appropriate.
          </p>
          <p>
            We do not guarantee uninterrupted access or that all
            website information will always be complete, current,
            or error-free. Nothing in these terms removes any
            rights or obligations that cannot lawfully be excluded.
          </p>
        </section>

        <section>
          <h2>9. Liability</h2>
          <p>
            Nothing in these terms excludes or limits liability,
            consumer rights, or other obligations to the extent
            that applicable law does not permit such exclusion
            or limitation.
          </p>
          <p>
            Any further allocation or limitation of liability must
            be reviewed against the law applicable to the identified
            website operator and the circumstances of use before
            these terms are finalised.
          </p>
        </section>

        <section>
          <h2>10. Privacy</h2>
          <p>
            Information about the marketing website's information
            handling is set out in the
            {' '}
            <Link to="/privacy">Privacy Policy</Link>.
            Separate Univa services may have additional privacy
            notices.
          </p>
        </section>

        <section>
          <h2>11. Governing law and disputes</h2>
          <p>
            The website operator's legal identity, applicable
            governing law, and appropriate dispute-resolution
            arrangements must be confirmed before a final governing-law
            clause is included. These draft terms do not designate
            a court or jurisdiction.
          </p>
        </section>

        <section>
          <h2>12. Changes to these terms</h2>
          <p>
            These terms may be revised as the website and its
            operating arrangements change. The date above identifies
            the date of this version. Any required notice of material
            changes will be handled in accordance with applicable law.
          </p>
        </section>

        <section>
          <h2>13. Contact</h2>
          <p>
            For general enquiries about this website, email
            {' '}
            <a href="mailto:support@univa.app">
              support@univa.app
            </a>.
          </p>
          <p>
            The final version should identify the responsible legal
            entity and its official contact details.
          </p>
        </section>
      </div>

      <div className="legal-page-footer">
        <Link to="/">Back to home</Link>
        <Link to="/privacy">Read Privacy Policy</Link>
        <Link to="/contact">Contact</Link>
      </div>
    </main>
  );
}
