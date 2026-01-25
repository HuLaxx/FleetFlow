import { NextResponse } from "next/server";

function getHealthUrl() {
  const fastapiUrl = process.env.FASTAPI_URL;
  if (fastapiUrl) {
    const base = fastapiUrl.replace(/\/api\/v1\/?$/, "");
    return `${base}/health`;
  }
  const port = process.env.API_PORT ?? "8000";
  return `http://localhost:${port}/health`;
}

export async function GET() {
  const url = getHealthUrl();
  try {
    const res = await fetch(url, { cache: "no-store" });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ status: "unreachable" }, { status: 503 });
  }
}
