import { NextRequest, NextResponse } from "next/server";

const PYTHON_API = process.env.PYTHON_API_URL || "http://127.0.0.1:5000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const response = await fetch(`${PYTHON_API}/api/translate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, message: "Failed to connect to translation server" },
      { status: 500 }
    );
  }
}
