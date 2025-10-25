import NextAuth, { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import GithubProvider from "next-auth/providers/github";
import { MongoClient, Db } from "mongodb";
import { JWT } from "next-auth/jwt";
import { Session } from "next-auth";

// Environment variable validation
if (!process.env.GOOGLE_CLIENT_ID || !process.env.GOOGLE_CLIENT_SECRET) {
  throw new Error(
    "Missing Google OAuth environment variables (GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET)",
  );
}

if (!process.env.GITHUB_CLIENT_ID || !process.env.GITHUB_CLIENT_SECRET) {
  console.warn(
    "GitHub OAuth not configured - GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET missing",
  );
}

if (!process.env.MONGODB_URI) {
  throw new Error("Missing MONGODB_URI environment variable");
}

if (!process.env.NEXTAUTH_SECRET) {
  throw new Error("Missing NEXTAUTH_SECRET environment variable");
}

// Type definitions
interface TokenData {
  email: string;
  name?: string | null;
  image?: string | null;
  accessToken: string;
  refreshToken?: string;
  expiresAt: number;
  tokenType: string;
  scope: string;
  savedAt: string;
}

interface RefreshedToken {
  accessToken: string;
  expiresAt: number;
  refreshToken: string;
}

// MongoDB connection management with connection pooling
class MongoDBConnection {
  private static instance: MongoDBConnection;
  private client: MongoClient | null = null;
  private db: Db | null = null;
  private isConnecting: boolean = false;
  private connectionPromise: Promise<Db> | null = null;

  private constructor() {}

  static getInstance(): MongoDBConnection {
    if (!MongoDBConnection.instance) {
      MongoDBConnection.instance = new MongoDBConnection();
    }
    return MongoDBConnection.instance;
  }

  async connect(): Promise<Db> {
    // Return existing database if already connected
    if (this.db && this.client) {
      return this.db;
    }

    // Return existing connection promise if connection is in progress
    if (this.isConnecting && this.connectionPromise) {
      return this.connectionPromise;
    }

    // Start new connection
    this.isConnecting = true;
    this.connectionPromise = this.performConnection();

    try {
      const db = await this.connectionPromise;
      this.isConnecting = false;
      return db;
    } catch (error) {
      this.isConnecting = false;
      this.connectionPromise = null;
      throw error;
    }
  }

  private async performConnection(): Promise<Db> {
    try {
      const mongoUri =
        process.env.MONGODB_URI || process.env.MONGODB_CONNECTION_STRING;
      if (!mongoUri) {
        throw new Error("MongoDB URI not configured");
      }

      this.client = new MongoClient(mongoUri, {
        maxPoolSize: 10,
        minPoolSize: 2,
        maxIdleTimeMS: 60000,
        serverSelectionTimeoutMS: 10000,
        socketTimeoutMS: 45000,
      });

      await this.client.connect();
      this.db = this.client.db(process.env.MONGODB_DB_NAME || "db1");
      console.log("✅ Connected to MongoDB");
      return this.db;
    } catch (error) {
      console.error("❌ MongoDB connection error:", error);
      this.client = null;
      this.db = null;
      throw error;
    }
  }

  async getDatabase(): Promise<Db> {
    try {
      return await this.connect();
    } catch (error) {
      console.error("Failed to get database connection:", error);
      // Retry once on connection failure
      this.client = null;
      this.db = null;
      return await this.connect();
    }
  }
}

const mongoConnection = MongoDBConnection.getInstance();

// Function to save token to MongoDB with retry logic
async function saveTokenToMongo(
  tokenData: TokenData,
  retries = 2,
): Promise<void> {
  for (let i = 0; i <= retries; i++) {
    try {
      const db = await mongoConnection.getDatabase();
      const collection = db.collection("secrets");

      await collection.updateOne(
        { email: tokenData.email },
        { $set: tokenData },
        { upsert: true },
      );

      console.log(`💾 Token saved to MongoDB for: ${tokenData.email}`);
      return;
    } catch (error) {
      console.error(
        `❌ Error saving token to MongoDB (attempt ${i + 1}):`,
        error,
      );
      if (i === retries) {
        // Don't throw on final retry - just log the error
        console.error("Failed to save token after all retries");
      } else {
        // Wait before retry
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }
  }
}

// Function to load token from MongoDB with retry logic
async function loadTokenFromMongo(
  email: string,
  retries = 2,
): Promise<TokenData | null> {
  for (let i = 0; i <= retries; i++) {
    try {
      const db = await mongoConnection.getDatabase();
      const collection = db.collection("secrets");

      const tokenData = (await collection.findOne({
        email,
      })) as TokenData | null;
      if (tokenData) {
        console.log("🔄 Restored refresh token from MongoDB");
        return tokenData;
      }
      return null;
    } catch (error) {
      console.error(
        `❌ Error loading token from MongoDB (attempt ${i + 1}):`,
        error,
      );
      if (i === retries) {
        return null;
      }
      // Wait before retry
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
  return null;
}

// Function to refresh Google access token with better timeout handling
async function refreshGoogleToken(
  refreshToken: string,
): Promise<RefreshedToken> {
  console.log("🔄 Starting token refresh...");

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000); // 15 second timeout

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
      signal: controller.signal,
    });

    clearTimeout(timeout);

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
    clearTimeout(timeout);
    if (error instanceof Error && error.name === "AbortError") {
      console.error("❌ Token refresh timed out");
      throw new Error("Token refresh timed out after 15 seconds");
    }
    console.error("❌ Error refreshing token:", error);
    throw error;
  }
}

// Optimized scope list - only include essential scopes initially
const GOOGLE_BASE_SCOPES = ["openid", "email", "profile"];

// Additional scopes that can be requested later via incremental authorization
const GOOGLE_ADDITIONAL_SCOPES = [
  // Gmail scopes
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/gmail.send",
  "https://www.googleapis.com/auth/gmail.modify",
  "https://www.googleapis.com/auth/gmail.compose",

  // Google Drive scopes
  "https://www.googleapis.com/auth/drive.file",
  "https://www.googleapis.com/auth/drive.metadata.readonly",

  // Google Calendar scopes
  "https://www.googleapis.com/auth/calendar.readonly",
  "https://www.googleapis.com/auth/calendar.events",
];

// Use all scopes if explicitly needed, otherwise start with base scopes
const useAllScopes = process.env.GOOGLE_USE_ALL_SCOPES === "true";

const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          prompt: "consent",
          access_type: "offline",
          response_type: "code",
          scope: useAllScopes
            ? [
                ...GOOGLE_BASE_SCOPES,
                ...GOOGLE_ADDITIONAL_SCOPES,
                // Additional comprehensive scopes if needed
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/documents",
                "https://www.googleapis.com/auth/presentations",
              ].join(" ")
            : [...GOOGLE_BASE_SCOPES, ...GOOGLE_ADDITIONAL_SCOPES].join(" "),
        },
      },
      // Increase timeout for token exchange
      httpOptions: {
        timeout: 15000, // 15 seconds
      },
    }),

    ...(process.env.GITHUB_CLIENT_ID && process.env.GITHUB_CLIENT_SECRET
      ? [
          GithubProvider({
            clientId: process.env.GITHUB_CLIENT_ID,
            clientSecret: process.env.GITHUB_CLIENT_SECRET,
            authorization: {
              params: {
                prompt: "consent",
                scope: "read:user user:email repo",
              },
            },
            httpOptions: {
              timeout: 10000, // 10 seconds
            },
          }),
        ]
      : []),
  ],
  secret: process.env.NEXTAUTH_SECRET,
  pages: {
    signIn: "/login",
    error: "/auth/error", // Add custom error page
  },
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  callbacks: {
    async signIn({ user, account }) {
      console.log("✅ Sign in successful:", {
        user: user.email,
        provider: account?.provider,
      });

      // Always allow sign in
      return true;
    },

    async jwt({ token, account, user }): Promise<JWT> {
      // Initial sign in
      if (account && user) {
        console.log("🔐 Initial sign in - storing tokens");
        const tokenData = {
          ...token,
          accessToken: account.access_token,
          refreshToken: account.refresh_token,
          expiresAt: account.expires_at,
          provider: account.provider,
          picture: user.image,
          name: user.name,
          email: user.email,
        };

        // Save initial token to MongoDB immediately
        if (
          account.provider === "google" &&
          account.refresh_token &&
          user.email
        ) {
          const saveData: TokenData = {
            email: user.email,
            name: user.name,
            image: user.image,
            accessToken: account.access_token!,
            refreshToken: account.refresh_token,
            expiresAt: account.expires_at!,
            tokenType: "Bearer",
            scope: account.scope || "",
            savedAt: new Date().toISOString(),
          };

          // Don't await - save asynchronously to avoid blocking sign in
          saveTokenToMongo(saveData).catch((err) =>
            console.error("Failed to save initial token:", err),
          );
        }

        return tokenData;
      }

      // For subsequent requests, check if we need to refresh
      try {
        // If no refresh token in current token, try to load from MongoDB
        if (!token.refreshToken && token.email && token.provider === "google") {
          const savedTokenData = await loadTokenFromMongo(
            token.email as string,
          );
          if (savedTokenData?.refreshToken) {
            console.log("📥 Loaded refresh token from MongoDB");
            token.refreshToken = savedTokenData.refreshToken;
            // Also update expiry if it's more recent
            if (savedTokenData.expiresAt) {
              token.expiresAt = savedTokenData.expiresAt;
            }
          }
        }

        // Check if token needs refresh
        const expiresAt = token.expiresAt as number | undefined;
        if (!expiresAt) {
          return token;
        }

        const timeUntilExpiry = expiresAt * 1000 - Date.now();
        const refreshThreshold = 5 * 60 * 1000; // 5 minutes

        // Only refresh Google tokens (GitHub tokens don't expire)
        if (
          timeUntilExpiry <= refreshThreshold &&
          token.refreshToken &&
          token.provider === "google"
        ) {
          console.log(
            `🔄 Token expiring soon (${Math.floor(timeUntilExpiry / 60000)} min), refreshing...`,
          );

          try {
            const refreshedTokens = await refreshGoogleToken(
              token.refreshToken as string,
            );

            const updatedToken = {
              ...token,
              accessToken: refreshedTokens.accessToken,
              expiresAt: refreshedTokens.expiresAt,
              refreshToken: refreshedTokens.refreshToken,
            };

            console.log(`✅ Token refreshed successfully`);

            // Save refreshed token to MongoDB asynchronously
            if (token.email) {
              const saveData: TokenData = {
                email: token.email as string,
                name: token.name as string,
                image: token.picture as string,
                accessToken: refreshedTokens.accessToken,
                refreshToken: refreshedTokens.refreshToken,
                expiresAt: refreshedTokens.expiresAt,
                tokenType: "Bearer",
                scope: "",
                savedAt: new Date().toISOString(),
              };

              saveTokenToMongo(saveData).catch((err) =>
                console.error("Failed to save refreshed token:", err),
              );
            }

            return updatedToken;
          } catch (error) {
            console.error("❌ Token refresh failed:", error);
            // Return token with error flag but don't throw
            return { ...token, error: "RefreshAccessTokenError" };
          }
        }

        return token;
      } catch (error) {
        console.error("Error in jwt callback:", error);
        return token;
      }
    },

    async session({ session, token }): Promise<Session> {
      // Extend session with custom properties
      const extendedSession = session as Session & {
        accessToken?: string;
        error?: string;
        provider?: string;
      };

      extendedSession.accessToken = token.accessToken as string | undefined;
      extendedSession.error = token.error as string | undefined;
      extendedSession.provider = token.provider as string | undefined;

      // Ensure user profile data is included
      if (session.user) {
        if (token.picture) {
          session.user.image = token.picture as string;
        }
        if (token.name) {
          session.user.name = token.name as string;
        }
        if (token.email) {
          session.user.email = token.email as string;
        }
      }

      // Log session status
      if (token.error) {
        console.log("⚠️ Session has error:", token.error);
      } else if (token.accessToken) {
        const expiresAt = token.expiresAt as number | undefined;
        if (expiresAt) {
          const minutesUntilExpiry = Math.floor(
            (expiresAt * 1000 - Date.now()) / 60000,
          );
          console.log(`✅ Session valid for ${minutesUntilExpiry} minutes`);
        }
      }

      return extendedSession;
    },

    async redirect({ url, baseUrl }) {
      // Allows relative callback URLs
      if (url.startsWith("/")) return `${baseUrl}${url}`;
      // Allows callback URLs on the same origin
      else if (new URL(url).origin === baseUrl) return url;
      return baseUrl;
    },
  },
  debug: process.env.NODE_ENV === "development",
  // Increase JWT max age to reduce token refresh frequency
  jwt: {
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
