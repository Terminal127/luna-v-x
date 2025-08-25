import React from "react";

const PrivacyPolicyPage = () => {
  return (
    <div className="bg-[#1a1b26] text-[#c0caf5] min-h-screen font-sans">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <header className="text-center mb-12">
          <h1 className="text-4xl sm:text-5xl font-extrabold bg-gradient-to-r from-[#bb9af7] via-[#7dcfff] to-[#9ece6a] bg-clip-text text-transparent pb-2">
            Privacy Policy
          </h1>
          <p className="text-[#565f89] mt-2 text-lg">
            Your privacy is critically important to us.
          </p>
          <p className="text-sm text-[#414868] mt-2">
            Last Updated: August 23, 2025
          </p>
        </header>

        <div className="space-y-8 text-[#a9b1d6] prose prose-invert prose-lg max-w-none">
          <section>
            <h2 className="text-2xl font-bold text-[#bb9af7]">
              1. Introduction
            </h2>
            <p>
              Welcome to our application ("we", "us", or "our"). We are
              committed to protecting your personal information and your right
              to privacy. This Privacy Policy explains how we collect, use,
              disclose, and safeguard your information when you use our
              application and connect to various Google services.
            </p>
            <p>
              By using our application, you agree to the collection and use of
              information in accordance with this policy. If you do not agree
              with the terms of this privacy policy, please do not access the
              application.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-[#bb9af7]">
              2. Information We Collect
            </h2>
            <p>
              When you grant us access to your Google account, we may collect
              and process the following information, depending on the specific
              services you authorize:
            </p>
            <ul className="list-disc list-inside space-y-2 pl-4">
              <li>
                <strong>Basic Profile Information:</strong> Your name, email
                address, and profile picture, as provided by your Google
                account. This is used to identify you within our application and
                personalize your experience.
              </li>
              <li>
                <strong>Service-Specific Data:</strong> We only access the data
                for which you explicitly grant permission. Our use of
                information received from Google APIs will adhere to the{" "}
                <a
                  href="https://developers.google.com/terms/api-services-user-data-policy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#7dcfff] hover:underline"
                >
                  Google API Services User Data Policy
                </a>
                , including the Limited Use requirements. The data includes:
                <ul className="list-disc list-inside space-y-2 pl-6 mt-2">
                  <li>
                    <strong>Gmail:</strong> Reading metadata of emails and
                    sending emails on your behalf. We do not store the content
                    of your emails.
                  </li>
                  <li>
                    <strong>Google Drive:</strong> Accessing, viewing, and
                    managing files and folders that you explicitly authorize.
                  </li>
                  <li>
                    <strong>Google Calendar:</strong> Viewing and managing your
                    calendar events.
                  </li>
                  <li>
                    <strong>Google Meet:</strong> Creating and managing video
                    meetings.
                  </li>
                  <li>
                    <strong>Google Docs, Sheets, Slides:</strong> Creating and
                    editing documents, spreadsheets, and presentations.
                  </li>
                  <li>
                    <strong>Google Photos:</strong> Viewing and managing your
                    photo library.
                  </li>
                  <li>
                    <strong>YouTube:</strong> Managing your YouTube account and
                    content.
                  </li>
                </ul>
              </li>
              <li>
                <strong>Authentication Tokens:</strong> We securely store access
                and refresh tokens provided by Google's OAuth 2.0 service. These
                tokens are essential for maintaining a persistent connection to
                your Google account and are stored in an encrypted format in our
                database.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-[#bb9af7]">
              3. How We Use Your Information
            </h2>
            <p>We use the information we collect for the following purposes:</p>
            <ul className="list-disc list-inside space-y-2 pl-4">
              <li>
                To provide, operate, and maintain the functionality of our
                application.
              </li>
              <li>
                To enable the integrations you have explicitly authorized with
                Google services.
              </li>
              <li>
                To personalize your experience and to allow us to deliver the
                type of content and product offerings in which you are most
                interested.
              </li>
              <li>
                To securely authenticate your account and prevent unauthorized
                access.
              </li>
              <li>
                To refresh your connection to Google services to ensure seamless
                operation, in accordance with Google's policies.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-[#bb9af7]">
              4. Data Sharing and Disclosure
            </h2>
            <p>
              We do not sell, trade, or otherwise transfer your personally
              identifiable information to outside parties. Your data is your
              own. We may share information under the following limited
              circumstances:
            </p>
            <ul className="list-disc list-inside space-y-2 pl-4">
              <li>
                <strong>With Your Consent:</strong> We will share your
                information with third parties only with your explicit consent.
              </li>
              <li>
                <strong>For Legal Reasons:</strong> We may disclose your
                information if required to do so by law or in response to valid
                requests by public authorities (e.g., a court or a government
                agency).
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-[#bb9af7]">
              5. Data Security
            </h2>
            <p>
              We have implemented a variety of security measures to maintain the
              safety of your personal information. Your data, including
              authentication tokens, is stored in a secure, encrypted database.
              All data transmission between our application and Google's
              services, as well as between your browser and our servers, is
              encrypted using Secure Socket Layer (SSL) technology.
            </p>
            <p>
              While we strive to use commercially acceptable means to protect
              your Personal Information, we cannot guarantee its absolute
              security.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-[#bb9af7]">
              6. Your Data Rights and Choices
            </h2>
            <p>
              You have complete control over the data you share with us. You
              can:
            </p>
            <ul className="list-disc list-inside space-y-2 pl-4">
              <li>
                <strong>Review and Update Permissions:</strong> You can review
                and manage the permissions you have granted to our application
                at any time by visiting your Google Account's{" "}
                <a
                  href="https://myaccount.google.com/permissions"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#7dcfff] hover:underline"
                >
                  Permissions Page
                </a>
                .
              </li>
              <li>
                <strong>Revoke Access:</strong> You can revoke our application's
                access to your Google account at any time from the same page.
                Revoking access will prevent us from accessing any further data,
                and the existing connection will be severed.
              </li>
              <li>
                <strong>Request Data Deletion:</strong> You can request the
                deletion of your account and all associated data from our
                systems by contacting us directly.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-[#bb9af7]">
              7. Changes to This Privacy Policy
            </h2>
            <p>
              We may update our Privacy Policy from time to time. We will notify
              you of any changes by posting the new Privacy Policy on this page.
              You are advised to review this Privacy Policy periodically for any
              changes. Changes to this Privacy Policy are effective when they
              are posted on this page.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-[#bb9af7]">8. Contact Us</h2>
            <p>
              If you have any questions or concerns about this Privacy Policy or
              our data practices, please do not hesitate to contact us at:
            </p>
            <p>
              <a
                href="mailto:privacy@yourdomain.com"
                className="text-[#7aa2f7] hover:underline"
              >
                privacy@yourdomain.com
              </a>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
};

export default PrivacyPolicyPage;
