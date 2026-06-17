import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getPythonApiUrl } from "@/lib/config";

const PYTHON_API = getPythonApiUrl();

export async function POST(request: NextRequest) {
  try {
    // Forward logout to Python backend (best-effort)
    await fetch(`${PYTHON_API}/api/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    }).catch(() => {});
  } catch {
    // Ignore backend errors — always clear the local cookie
  }

  // Clear the JWT cookie set on login
  const cookieStore = await cookies();
  cookieStore.delete("access_token_cookie");

  return NextResponse.json({ success: true });
}
