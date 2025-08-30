// app/api/auth/signup/route.ts

import { NextResponse } from "next/server";
import { hash } from "bcryptjs";
import { MongoClient } from "mongodb";

async function connectToDatabase() {
  // IMPORTANT: Ensure your MONGO_URI is in your .env.local file
  const client = await MongoClient.connect(process.env.MONGO_URI!);
  return client;
}

export async function POST(request: Request) {
  try {
    const { email, password } = await request.json();

    // --- Input Validation ---
    if (!email || !email.includes("@")) {
      return NextResponse.json(
        { message: "Invalid email format." },
        { status: 422 },
      );
    }
    if (!password || password.trim().length < 8) {
      return NextResponse.json(
        { message: "Password must be at least 8 characters long." },
        { status: 422 },
      );
    }

    let client;
    try {
      client = await connectToDatabase();
    } catch (error) {
      console.error("Database connection failed:", error);
      return NextResponse.json(
        { message: "Could not connect to the database." },
        { status: 500 },
      );
    }

    const db = client.db();
    const usersCollection = db.collection("users");

    // --- Check if user already exists ---
    const existingUser = await usersCollection.findOne({ email: email });
    if (existingUser) {
      await client.close();
      return NextResponse.json(
        { message: "A user with this email already exists!" },
        { status: 422 },
      );
    }

    // --- Hash the password for security ---
    const hashedPassword = await hash(password, 12);

    // --- Store the new user ---
    await usersCollection.insertOne({
      email: email,
      password: hashedPassword,
      createdAt: new Date(),
    });

    await client.close();
    return NextResponse.json(
      { message: "Successfully created user!" },
      { status: 201 },
    );
  } catch (error) {
    console.error("User creation failed:", error);
    return NextResponse.json(
      { message: "Something went wrong during signup." },
      { status: 500 },
    );
  }
}
