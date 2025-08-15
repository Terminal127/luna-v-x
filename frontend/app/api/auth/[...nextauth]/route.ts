import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import GithubProvider from "next-auth/providers/github";
import { writeFileSync, mkdirSync, readFileSync, existsSync } from "fs";
import path from "path";

// Check for missing critical variables
if (!process.env.GOOGLE_CLIENT_ID || !process.env.GOOGLE_CLIENT_SECRET) {
  throw new Error(
    "Missing Google OAuth environment variables (GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET)",
  );
}

// Function to refresh Google access token
async function refreshGoogleToken(refreshToken: string): Promise<any> {
  console.log("🔄 Starting token refresh...");
  try {
    const response = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        client_id: process.env.GOOGLE_CLIENT_ID!,
        client_secret: process.env.GOOGLE_CLIENT_SECRET!,
        refresh_token: refreshToken,
        grant_type: "refresh_token",
      }),
    });

    const tokens = await response.json();
    console.log("🔄 Token refresh response status:", response.status);

    if (!response.ok) {
      console.error("❌ Token refresh failed:", tokens);
      throw new Error(
        `Token refresh failed: ${tokens.error_description || tokens.error}`,
      );
    }

    console.log("✅ Token refresh successful!");

    return {
      accessToken: tokens.access_token,
      expiresAt: Math.floor(Date.now() / 1000) + tokens.expires_in,
      refreshToken: refreshToken, // Keep the same refresh token
    };
  } catch (error) {
    console.error("❌ Error refreshing token:", error);
    throw error;
  }
}

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          prompt: "consent",
          access_type: "offline",
          scope:
            "openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send",
        },
      },
    }),
    GithubProvider({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
      authorization: {
        params: {
          prompt: "consent",
          access_type: "offline",
        },
      },
    }),
  ],
  secret: process.env.NEXTAUTH_SECRET,
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, account, user }) {
      // Initial sign in
      if (account && user) {
        return {
          ...token,
          accessToken: account.access_token,
          refreshToken: account.refresh_token,
          expiresAt: account.expires_at,
          provider: account.provider,
          picture: user.image,
          name: user.name,
          email: user.email,
        };
      }

      // If no refresh token in current token, try to load from saved file
      if (!token.refreshToken && token.email) {
        try {
          const tokensDir = path.join(process.cwd(), "saved-tokens");
          const filePath = path.join(tokensDir, "google_token.json");

          if (existsSync(filePath)) {
            const savedTokenData = JSON.parse(readFileSync(filePath, "utf8"));
            if (
              savedTokenData.refreshToken &&
              savedTokenData.email === token.email
            ) {
              console.log("🔄 Restored refresh token from saved file");
              token.refreshToken = savedTokenData.refreshToken;
            }
          }
        } catch (error) {
          console.error("❌ Error loading saved refresh token:", error);
        }
      }

      // Check if token needs refresh (5 minutes before expiry)
      const timeUntilExpiry = (token.expiresAt as number) * 1000 - Date.now();
      const minutesUntilExpiry = Math.floor(timeUntilExpiry / 60000);
      const refreshThreshold = 53 * 60 * 1000; // 5 minutes in milliseconds

      console.log(`🔍 Token check: ${minutesUntilExpiry} minutes until expiry`);
      console.log(
        `🔍 Debug - timeUntilExpiry: ${timeUntilExpiry}ms, threshold: ${refreshThreshold}ms`,
      );
      console.log(`🔍 Debug - refreshToken exists: ${!!token.refreshToken}`);
      console.log(`🔍 Debug - provider: ${token.provider}`);

      // Refresh token if it expires within 22 minutes
      if (
        timeUntilExpiry <= refreshThreshold &&
        token.refreshToken &&
        token.provider === "google"
      ) {
        console.log(`🔄 Token expires soon for google! Refreshing...`);
        try {
          const refreshedTokens = await refreshGoogleToken(
            token.refreshToken as string,
          );

          const newExpiryTime = new Date(refreshedTokens.expiresAt * 1000);
          console.log(
            `🎉 Token refreshed successfully! New expiry: ${newExpiryTime.toLocaleString()}`,
          );

          return {
            ...token,
            accessToken: refreshedTokens.accessToken,
            expiresAt: refreshedTokens.expiresAt,
            refreshToken: refreshedTokens.refreshToken,
            picture: token.picture,
            name: token.name,
            email: token.email,
          };
        } catch (error) {
          console.error("❌ Error refreshing access token", error);
          return { ...token, error: "RefreshAccessTokenError" };
        }
      }

      // Token is still valid
      if (timeUntilExpiry > refreshThreshold) {
        console.log(`✅ Token still valid for ${minutesUntilExpiry} minutes`);
      }

      return token;
    },
    async session({ session, token }) {
      // Send properties to the client
      (session as any).accessToken = token.accessToken;
      (session as any).error = token.error;

      // Ensure user profile data is included
      if (session.user && token.picture) {
        session.user.image = token.picture as string;
      }

      // Save updated token to file
      if (
        session.user?.email &&
        token.accessToken &&
        token.provider === "google"
      ) {
        try {
          const tokensDir = path.join(process.cwd(), "saved-tokens");
          mkdirSync(tokensDir, { recursive: true });

          const sanitizedEmail = session.user.email
            .replace("@", "_at_")
            .replace(/\./g, "_");
          const filename = `google_token.json`;
          const filePath = path.join(tokensDir, filename);

          const tokenData = {
            email: session.user.email,
            name: session.user.name,
            image: session.user.image,
            accessToken: token.accessToken,
            refreshToken: token.refreshToken,
            expiresAt: token.expiresAt,
            tokenType: "Bearer",
            scope:
              "openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send",
            savedAt: new Date().toISOString(),
          };

          writeFileSync(filePath, JSON.stringify(tokenData, null, 2));

          const expiryTime = new Date((token.expiresAt as number) * 1000);
          console.log(`💾 Token saved for: ${session.user.email}`);
          console.log(`📅 Token expires at: ${expiryTime.toLocaleString()}`);
          console.log(
            `🔑 Access token preview: ${String(token.accessToken).substring(0, 20)}...`,
          );
        } catch (error) {
          console.error("❌ Error saving refreshed token:", error);
        }
      }

      return session;
    },
    async signIn({ user, account, profile }) {
      console.log("Sign in attempt:", {
        user: user.email,
        account: account?.provider,
      });
      return true;
    },
  },
  debug: process.env.NODE_ENV === "development",
});

export { handler as GET, handler as POST };
