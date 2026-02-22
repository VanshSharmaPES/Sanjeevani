import { NextRequest, NextResponse } from "next/server";

const PYTHON_API = process.env.PYTHON_API_URL || "http://localhost:5000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const { userId } = await params;
    const response = await fetch(`${PYTHON_API}/api/history/${userId}`);
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, message: "Failed to connect to server" },
      { status: 500 }
    );
  }
}
