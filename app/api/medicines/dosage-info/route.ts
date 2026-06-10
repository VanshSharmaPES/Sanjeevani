import { NextRequest, NextResponse } from "next/server";

const PYTHON_API = process.env.PYTHON_API_URL || "http://127.0.0.1:5000";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const name = searchParams.get("name") || "";
    const composition = searchParams.get("composition") || "";

    const response = await fetch(
      `${PYTHON_API}/api/medicines/dosage-info?name=${encodeURIComponent(name)}&composition=${encodeURIComponent(composition)}`,
      { method: "GET" }
    );

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, message: "Failed to connect to server" },
      { status: 500 }
    );
  }
}
