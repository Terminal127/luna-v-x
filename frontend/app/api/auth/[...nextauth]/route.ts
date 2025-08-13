import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";

// --- DEBUGGING ---
console.log("--- NextAuth Configuration ---");
console.log(
  "GOOGLE_CLIENT_ID:",
  process.env.GOOGLE_CLIENT_ID ? "Loaded" : "NOT LOADED",
);
console.log(
  "GOOGLE_CLIENT_SECRET:",
  process.env.GOOGLE_CLIENT_SECRET ? "Loaded" : "NOT LOADED",
);
console.log(
  "NEXTAUTH_SECRET:",
  process.env.NEXTAUTH_SECRET ? "Loaded" : "NOT LOADED",
);
console.log(
  "NEXTAUTH_URL:",
  process.env.NEXTAUTH_URL ? "Loaded" : "NOT LOADED",
);
console.log("----------------------------");

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
    }),
  ],
  secret: process.env.NEXTAUTH_SECRET,
  callbacks: {
    async signIn({ user, account, profile }) {
      console.log("Sign in attempt:", {
        user: user.email,
        account: account?.provider,
      });
      return true;
    },
    async session({ session, token }) {
      console.log("Session created for:", session.user?.email);
      return session;
    },
  },
  debug: process.env.NODE_ENV === "development", // Enable debug logs in development
});

export { handler as GET, handler as POST };
