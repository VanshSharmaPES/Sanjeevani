import { NextRequest, NextResponse } from "next/server";
import { getPythonApiUrl } from "@/lib/config";

const PYTHON_API = getPythonApiUrl();

export async function GET(request: NextRequest) {
  const name = new URL(request.url).searchParams.get("name") || "";
  try {
    const response = await fetch(
      `${PYTHON_API}/api/medicines/alternatives?name=${encodeURIComponent(name)}`,
      { cache: "no-store" },
    );
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ error: "Failed to connect to server" }, { status: 502 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const response = await fetch(`${PYTHON_API}/api/medicines/alternatives`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: request.headers.get("cookie") || "",
      },
      body: JSON.stringify(await request.json()),
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ success: false, message: "Failed to connect to server" }, { status: 502 });
  }
}
