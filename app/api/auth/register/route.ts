import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const PYTHON_API = process.env.PYTHON_API_URL || "http://127.0.0.1:5000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(`${PYTHON_API}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    // Pass the Set-Cookie exactly as formatted by flask-jwt-extended
    const setCookie = response.headers.get("set-cookie");
    if (setCookie) {
      const cookieParts = setCookie.split(';');
      let cookieValue = cookieParts[0].split('=')[1] || '';
      let cookieName = cookieParts[0].split('=')[0] || '';
      if (cookieName && cookieValue !== undefined) {
        const cookieStore = await cookies();
        cookieStore.set({
          name: cookieName,
          value: cookieValue,
          httpOnly: true,
          secure: process.env.NODE_ENV === "production",
          sameSite: "lax", // Relax to strict locally if ports differ
          path: "/",
        });
      }
    }

    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, message: "Failed to connect to server" },
      { status: 500 }
    );
  }
}
