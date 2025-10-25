"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function AuthErrorPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [countdown, setCountdown] = useState(5);

  const error = searchParams.get("error");

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          router.push("/login");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [router]);

  const getErrorMessage = () => {
    switch (error) {
      case "OAuthCallback":
        return {
          title: "Authentication Timeout",
          description:
            "The authentication process took too long. This can happen when requesting many permissions at once. Please try again.",
          suggestions: [
            "Check your internet connection",
            "Try signing in with fewer permissions",
            "Clear your browser cookies and try again",
            "Contact support if the issue persists",
          ],
        };
      case "OAuthSignin":
        return {
          title: "Sign In Failed",
          description:
            "There was a problem signing you in. Please check your credentials and try again.",
          suggestions: [
            "Verify your OAuth app is properly configured",
            "Check that your account has the necessary permissions",
            "Try a different sign-in method",
          ],
        };
      case "OAuthAccountNotLinked":
        return {
          title: "Account Already Exists",
          description:
            "This email is already associated with another account. Please sign in with the original provider.",
          suggestions: [
            "Try signing in with the provider you originally used",
            "Contact support to link your accounts",
          ],
        };
      case "EmailSignin":
        return {
          title: "Email Sign In Failed",
          description:
            "We couldn't send the sign-in email. Please check your email address and try again.",
          suggestions: [
            "Verify your email address is correct",

            "Check your spam folder",
            "Try a different sign-in method",
          ],
        };
      case "CredentialsSignin":
        return {
          title: "Invalid Credentials",
          description: "The username or password you entered is incorrect.",
          suggestions: [
            "Check your username and password",
            "Reset your password if you've forgotten it",
            "Contact support if you're unable to sign in",
          ],
        };
      case "SessionRequired":
        return {
          title: "Session Required",
          description: "You need to be signed in to access this page.",
          suggestions: [
            "Sign in to continue",
            "Create an account if you don't have one",
          ],
        };
      default:
        return {
          title: "Authentication Error",
          description:
            "An unexpected error occurred during authentication. Please try again.",
          suggestions: [
            "Clear your browser cache and cookies",
            "Try a different browser",
            "Contact support if the problem persists",
          ],
        };
    }
  };

  const errorInfo = getErrorMessage();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <div className="max-w-md w-full mx-4">
        <div className="bg-gray-800/50 backdrop-blur-lg rounded-2xl shadow-2xl border border-gray-700 p-8">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-red-500/20 rounded-full mb-4">
              <svg
                className="w-8 h-8 text-red-500"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>

            <h1 className="text-2xl font-bold text-white mb-2">
              {errorInfo.title}
            </h1>

            <p className="text-gray-400 mb-6">{errorInfo.description}</p>

            {error && (
              <div className="bg-gray-900/50 rounded-lg p-3 mb-6">
                <code className="text-sm text-gray-500">
                  Error Code: {error}
                </code>
              </div>
            )}
          </div>

          <div className="space-y-3 mb-6">
            <h3 className="text-sm font-semibold text-gray-300">
              Suggestions:
            </h3>
            <ul className="space-y-2">
              {errorInfo.suggestions.map((suggestion, index) => (
                <li key={index} className="flex items-start">
                  <svg
                    className="w-5 h-5 text-blue-400 mt-0.5 mr-2 flex-shrink-0"
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path d="M9 5l7 7-7 7" />
                  </svg>
                  <span className="text-sm text-gray-400">{suggestion}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-3">
            <button
              onClick={() => router.push("/login")}
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-3 px-4 rounded-lg font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              Try Again
            </button>

            <button
              onClick={() => router.push("/")}
              className="w-full bg-gray-700 text-gray-300 py-3 px-4 rounded-lg font-medium hover:bg-gray-600 transition-colors duration-200"
            >
              Go to Homepage
            </button>
          </div>

          <div className="text-center mt-6">
            <p className="text-sm text-gray-500">
              Redirecting to login in {countdown} seconds...
            </p>
          </div>
        </div>

        <div className="text-center mt-6">
          <p className="text-sm text-gray-500">
            Need help?{" "}
            <a
              href="/support"
              className="text-blue-400 hover:text-blue-300 transition-colors"
            >
              Contact Support
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
