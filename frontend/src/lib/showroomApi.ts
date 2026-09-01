// SESSION_226 — public showroom API client.
//
// Backs the customer-facing showroom, homepage teaser, and hero
// visuals. Talks to the AllowAny endpoint
// ``GET /api/dealer-ai/showroom/vehicles/`` (added SESSION_226 in
// `views_showroom.py`) — no auth required, must NOT use
// authFetch. Session cookies are not sent so a broken session
// cannot break a customer page.

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/dealer-ai";

export type ShowroomCondition = "new" | "used" | "certified";

export interface ShowroomVehicle {
  /** 17-char VIN, or "" when the source row has none. */
  vin: string;
  stock_number: string;
  year: number;
  make: string;
  model: string;
  trim: string;
  condition: ShowroomCondition | string;
  drivetrain: string;
  fuel_type: string;
  exterior_color: string;
  mileage: number;
  /** Decimal-as-string; parseFloat before doing math. */
  price: string;
  /** Sticker; null on used-only lots. */
  msrp: string | null;
  /** Operator-set stock photo. May be empty on demo seeds. */
  image_url: string;
  /** Vehicle Detail Page URL. May be empty. */
  vdp_url: string;
  /** Pre-computed "2024 Ford Escape Titanium" label. */
  display_name: string;
}

export interface ShowroomListResponse {
  count: number;
  limit: number;
  offset: number;
  results: ShowroomVehicle[];
}

export interface ShowroomListFilters {
  q?: string;
  limit?: number;
  offset?: number;
}

export async function listShowroomVehicles(
  filters: ShowroomListFilters = {},
): Promise<ShowroomListResponse> {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters.offset !== undefined)
    params.set("offset", String(filters.offset));
  const qs = params.toString();
  const res = await fetch(
    `${API_BASE}/showroom/vehicles/${qs ? `?${qs}` : ""}`,
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `showroom list failed (${res.status}): ${text.slice(0, 500)}`,
    );
  }
  return res.json() as Promise<ShowroomListResponse>;
}
