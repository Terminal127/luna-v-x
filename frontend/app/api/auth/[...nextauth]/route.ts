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

    if (!response.ok) {
      throw new Error(
        `Token refresh failed: ${tokens.error_description || tokens.error}`,
      );
    }

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
          prompt: "select_account",
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
          prompt: "select_account",
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

      // Return previous token if access token has not expired yet
      if (Date.now() < (token.expiresAt as number) * 1000) {
        return token;
      }

      // Access token has expired, try to refresh it
      if (token.refreshToken && token.provider === "google") {
        try {
          const refreshedTokens = await refreshGoogleToken(
            token.refreshToken as string,
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
          console.error("Error refreshing access token", error);
          return { ...token, error: "RefreshAccessTokenError" };
        }
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
          console.log(
            `✅ Token refreshed and saved for: ${session.user.email}`,
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
