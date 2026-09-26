import { NextRequest, NextResponse } from "next/server";
import { authenticatedFetch } from "../../../lib/server-api";

export async function POST(request: NextRequest) {
  const payload = await request.json();

  const quoteResponse = await authenticatedFetch("/quotes", {
    method: "POST",
    body: JSON.stringify(payload)
  });
  const quote = await quoteResponse.json();
  if (!quoteResponse.ok) {
    return NextResponse.json(quote, { status: quoteResponse.status });
  }

  const bookingResponse = await authenticatedFetch("/bookings", {
    method: "POST",
    headers: {
      "Idempotency-Key": crypto.randomUUID()
    },
    body: JSON.stringify({ quote_id: quote.id })
  });
  const booking = await bookingResponse.json();
  if (!bookingResponse.ok) {
    return NextResponse.json(booking, { status: bookingResponse.status });
  }

  return NextResponse.json({ quote, booking }, { status: 201 });
}
