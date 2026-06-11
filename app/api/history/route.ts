import { NextRequest, NextResponse } from "next/server";
import { getPythonApiUrl } from "@/lib/config";

const PYTHON_API = getPythonApiUrl();

export async function GET(request: NextRequest) {
    try {
        const cookie = request.headers.get("cookie") || "";
        const response = await fetch(`${PYTHON_API}/api/history`, {
            headers: { "Cookie": cookie }
        });
        const data = await response.json();
        return NextResponse.json(data, { status: response.status });
    } catch (error: any) {
        return NextResponse.json(
            { success: false, message: "Failed to connect to server" },
            { status: 500 }
        );
    }
}
