import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import GithubProvider from "next-auth/providers/github";
import { MongoClient } from "mongodb";

if (
  !process.env.GOOGLE_CLIENT_ID ||
  !process.env.GOOGLE_CLIENT_SECRET ||
  !process.env.MONGODB_URI
) {
  throw new Error(
    "Missing Google OAuth environment variables (GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET or MONGODB_URI)",
  );
}

const client = new MongoClient(process.env.MONGODB_URI);

async function getDatabase() {
  await client.connect();
  return client.db("db1");
}

async function saveTokenToMongo(tokenData: any) {
  try {
    const db = await getDatabase();
    const collection = db.collection("secrets");
    await collection.updateOne(
      { email: tokenData.email },
      { $set: tokenData },
      { upsert: true },
    );
    console.log(`💾 Token saved to MongoDB for: ${tokenData.email}`);
  } catch (error) {
    console.error("❌ Error saving token to MongoDB:", error);
  }
}

async function loadTokenFromMongo(email: string) {
  try {
    const db = await getDatabase();
    const collection = db.collection("secrets");
    const tokenData = await collection.findOne({ email });
    if (tokenData) {
      console.log("🔄 Restored token data from MongoDB");
      return tokenData;
    }
    return null;
  } catch (error) {
    console.error("❌ Error loading token from MongoDB:", error);
    return null;
  }
}

async function refreshGoogleToken(refreshToken: string): Promise<any> {
  console.log("🔄 Starting token refresh...");
  try {
    const response = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: process.env.GOOGLE_CLIENT_ID!,
        client_secret: process.env.GOOGLE_CLIENT_SECRET!,
        refresh_token: refreshToken,
        grant_type: "refresh_token",
      }),
    });
    const tokens = await response.json();
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
      refreshToken: refreshToken,
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
          scope: "openid email profile",
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
      if (account) {
        const currentScopes = token.scope
          ? (token.scope as string).split(" ")
          : [];
        const newScopes = account.scope ? account.scope.split(" ") : [];
        const allScopes = [...new Set([...currentScopes, ...newScopes])].join(
          " ",
        );

        return {
          ...token,
          accessToken: account.access_token,
          refreshToken: account.refresh_token ?? token.refreshToken,
          expiresAt: account.expires_at,
          provider: account.provider,
          scope: allScopes,
          ...(user && {
            picture: user.image,
            name: user.name,
            email: user.email,
          }),
        };
      }

      if (Date.now() >= (token.expiresAt as number) * 1000) {
        console.log("Token has expired, attempting to refresh...");
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
            };
          } catch (error) {
            console.error("Error refreshing access token", error);
            return { ...token, error: "RefreshAccessTokenError" };
          }
        }
      }

      return token;
    },
    async session({ session, token }) {
      (session as any).accessToken = token.accessToken;
      (session as any).error = token.error;
      (session as any).scope = token.scope;
      if (session.user && token.picture) {
        session.user.image = token.picture as string;
      }

      if (
        session.user?.email &&
        token.accessToken &&
        token.provider === "google"
      ) {
        const tokenData = {
          email: session.user.email,
          name: session.user.name,
          image: session.user.image,
          accessToken: token.accessToken,
          refreshToken: token.refreshToken,
          expiresAt: token.expiresAt,
          tokenType: "Bearer",
          scope: token.scope,
          savedAt: new Date().toISOString(),
        };
        await saveTokenToMongo(tokenData);
      }

      return session;
    },
    async signIn({ user, account, profile }) {
      console.log(user, account, profile);
      return true;
    },
  },
  debug: process.env.NODE_ENV === "development",
});

export { handler as GET, handler as POST };
