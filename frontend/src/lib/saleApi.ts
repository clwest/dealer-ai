// Milestone 9 · Increment 5 (SESSION_104) — Sale + Delivery API client.
//
// Consumes the three per-vehicle admin endpoints shipped M9.1 + M9.2:
//
//   POST /admin/vehicles/<stock>/sale/         (M9.1)
//   POST /admin/vehicles/<stock>/delivery/     (M9.2)
//   PATCH /admin/deliveries/<id>/              (M9.2)
//
// Money handling: same convention as analyticsApi.ts — every dollar
// figure travels as a two-decimal-place string on the wire and stays
// a string in this module. The backend is authoritative.
//
// Kept as its own module (rather than folded into lib/api.ts)
// because api.ts already exceeds 2000 lines and Sale + Delivery are
// a discrete M9 surface with their own row-type vocabulary.

import {
  ApiError,
  authGetJSON,
  authPatchJSON,
  authPostJSON,
} from "@/lib/authFetch";


// Local helper — "was this a 404 from the backend?" — used to map
// GET reads of "not created yet" resources into a null return
// rather than an exception the page has to catch and branch on.
function isApi404(err: unknown): boolean {
  return err instanceof ApiError && err.status === 404;
}

// ---------------------------------------------------------------------------
// Sale
// ---------------------------------------------------------------------------

export type SaleFinanceType = "cash" | "retail" | "bhph";

export interface Sale {
  id: number;
  vehicle_stock: string;
  buyer_id: number | null;
  sale_date: string; // ISO date
  sold_price: string; // Decimal-as-string
  finance_type: SaleFinanceType;
  lender_name: string;
  gross_realized: string; // Decimal-as-string, signed
  created_at: string;
  updated_at: string;
}

export interface CreateSaleRequest {
  sale_date: string; // ISO date
  sold_price: string;
  finance_type: SaleFinanceType;
  buyer_id?: number | null;
  lender_name?: string;
}

interface CreateSaleResponse {
  sale: Sale;
}

export async function createSale(
  stockNumber: string,
  payload: CreateSaleRequest,
): Promise<Sale> {
  const response = await authPostJSON<CreateSaleResponse>(
    `/admin/vehicles/${encodeURIComponent(stockNumber)}/sale/`,
    payload,
  );
  return response.sale;
}

// Read the Sale for this vehicle. Returns null when the vehicle
// has no Sale yet (404 → null is the natural read shape; the
// caller renders a create form instead).
export async function readSale(stockNumber: string): Promise<Sale | null> {
  try {
    const response = await authGetJSON<CreateSaleResponse>(
      `/admin/vehicles/${encodeURIComponent(stockNumber)}/sale/`,
    );
    return response.sale;
  } catch (err) {
    // Anything else — auth / server / unknown — bubbles up so the
    // page can render an error state distinct from "not created yet."
    if (isApi404(err)) return null;
    throw err;
  }
}

// ---------------------------------------------------------------------------
// Delivery
// ---------------------------------------------------------------------------

export type DeliveryChecklistKey =
  | "detail_booked"
  | "fueled"
  | "temp_tag"
  | "insurance_verified"
  | "customer_walkthrough";

export interface DeliveryChecklist {
  detail_booked: boolean;
  fueled: boolean;
  temp_tag: boolean;
  insurance_verified: boolean;
  customer_walkthrough: boolean;
}

export interface Delivery {
  id: number;
  sale_id: number;
  vehicle_stock: string;
  delivery_date: string | null; // ISO date or null
  checklist: DeliveryChecklist;
  temp_tag_number: string;
  insurance_verified: boolean;
  insurance_verified_at: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface CreateDeliveryRequest {
  delivery_date?: string | null;
  temp_tag_number?: string;
  notes?: string;
}

interface DeliveryResponse {
  delivery: Delivery;
}

export async function createDelivery(
  stockNumber: string,
  payload: CreateDeliveryRequest = {},
): Promise<Delivery> {
  const response = await authPostJSON<DeliveryResponse>(
    `/admin/vehicles/${encodeURIComponent(stockNumber)}/delivery/`,
    payload,
  );
  return response.delivery;
}

// Read the Delivery for this vehicle. Returns null when no Delivery
// exists yet (or the vehicle has no Sale — the backend surfaces both
// as 404).
export async function readDelivery(
  stockNumber: string,
): Promise<Delivery | null> {
  try {
    const response = await authGetJSON<DeliveryResponse>(
      `/admin/vehicles/${encodeURIComponent(stockNumber)}/delivery/`,
    );
    return response.delivery;
  } catch (err) {
    if (isApi404(err)) return null;
    throw err;
  }
}

export interface UpdateDeliveryRequest {
  delivery_date?: string | null;
  temp_tag_number?: string;
  notes?: string;
  checklist_key?: DeliveryChecklistKey;
  checklist_value?: boolean;
  verify_insurance?: boolean;
}

export async function updateDelivery(
  deliveryId: number,
  payload: UpdateDeliveryRequest,
): Promise<Delivery> {
  const response = await authPatchJSON<DeliveryResponse>(
    `/admin/deliveries/${deliveryId}/`,
    payload,
  );
  return response.delivery;
}
