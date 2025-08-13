import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import GithubProvider from "next-auth/providers/github";
import { writeFileSync, mkdirSync } from "fs";
import path from "path";

// Check for missing critical variables
if (!process.env.GOOGLE_CLIENT_ID || !process.env.GOOGLE_CLIENT_SECRET) {
  throw new Error(
    "Missing Google OAuth environment variables (GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET)",
  );
}

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          scope:
            "openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send",
        },
      },
    }),
    GithubProvider({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    }),
  ],
  secret: process.env.NEXTAUTH_SECRET,
  callbacks: {
    async signIn({ user, account, profile }) {
      console.log("Sign in attempt:", {
        user: user.email,
        account: account?.provider,
      });

      // Save Google token to file when user signs in
      if (
        account &&
        account.provider === "google" &&
        account.access_token &&
        user?.email
      ) {
        try {
          // Create tokens directory if it doesn't exist
          const tokensDir = path.join(process.cwd(), "saved-tokens");
          mkdirSync(tokensDir, { recursive: true });

          // Prepare token data
          const tokenData = {
            email: user.email,
            accessToken: account.access_token,
            refreshToken: account.refresh_token,
            expiresAt: account.expires_at,
            tokenType: account.token_type,
            scope: account.scope,
            savedAt: new Date().toISOString(),
          };

          // Create filename (sanitize email for filesystem)
          const sanitizedEmail = user.email
            .replace("@", "_at_")
            .replace(/\./g, "_");
          const filename = `google_token_${sanitizedEmail}.json`;
          const filePath = path.join(tokensDir, filename);

          // Save to file
          writeFileSync(filePath, JSON.stringify(tokenData, null, 2));
          console.log(`✅ Google token saved to: ${filePath}`);
        } catch (error) {
          console.error("❌ Error saving Google token:", error);
        }
      }

      return true;
    },
    async session({ session, token }) {
      console.log("Session created for:", session.user?.email);
      return session;
    },
  },
  debug: process.env.NODE_ENV === "development",
});

export { handler as GET, handler as POST };
