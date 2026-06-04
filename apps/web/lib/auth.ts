import { type NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    CredentialsProvider({
      name: "OTP",
      credentials: {
        accessToken:  { label: "Access Token",  type: "text" },
        refreshToken: { label: "Refresh Token", type: "text" },
        userId:       { label: "User ID",        type: "text" },
      },
      async authorize(credentials) {
        if (!credentials?.accessToken) return null;
        return {
          id:           credentials.userId ?? "",
          accessToken:  credentials.accessToken,
          refreshToken: credentials.refreshToken ?? "",
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, user }) {
      // OTP sign-in — credentials are already pre-verified by our backend
      if (user && "accessToken" in user) {
        token.accessToken  = (user as Record<string, unknown>).accessToken as string;
        token.refreshToken = (user as Record<string, unknown>).refreshToken as string;
        token.userId       = user.id;
      }

      // Google OAuth — exchange Google id_token with our backend
      if (account?.provider === "google" && account.id_token && user?.email) {
        try {
          const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}/auth/google`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              id_token:  account.id_token,
              email:     user.email,
              full_name: user.name,
            }),
          });
          const data = await res.json();
          if (data.access_token) {
            token.accessToken  = data.access_token;
            token.refreshToken = data.refresh_token;
            token.userId       = data.user_id;
          }
        } catch {
          // Google OAuth handled gracefully
        }
      }

      return token;
    },
    async session({ session, token }) {
      session.accessToken  = token.accessToken as string;
      session.refreshToken = token.refreshToken as string;
      session.userId       = token.userId as string;
      return session;
    },
  },
  pages: {
    signIn: "/login",
    error:  "/login",
  },
  session: { strategy: "jwt" },
  secret: process.env.NEXTAUTH_SECRET,
};
