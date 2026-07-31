// SESSION_030 pivot — Copper Canyon Auto sample inventory.
//
// Replaces frontend/src/data/freedomFordInventorySample.ts (deleted
// in the same commit). This is **sample data for UI/demo realism
// only**. The Live Assistant page still fetches real inventory
// through the backend chat APIs and is not affected by this file.
//
// Stock numbers mirror the backend Copper Canyon seed
// (`python manage.py seed_copper_canyon_demo`) so a demo that runs
// both frontend and backend stays consistent. The subset here is 12
// units chosen for visual variety across the persona's shape:
// mid-range trucks, family SUVs, commuter cars, and a family van.
//
// Persona: Copper Canyon Auto (Yuma, AZ). Every unit is a used
// mixed-make vehicle sourced through auctions / trades / private-
// party acquisitions. No new inventory, no OEM CPO. See
// `docs/INDEPENDENT_DEALER_PIVOT.md`.
//
// Image URLs are Unsplash placeholders sized for card thumbnails;
// they don't necessarily match the exact trim / color of the
// listed unit — they're stand-ins until Phase 4+ ships real
// dealer-uploaded photos through the CRM feed.

export type VehicleCondition = "new" | "used" | "certified";

export interface SampleInventoryVehicle {
  /** 17-char VIN — stable key. Real dealers get these from CRM;
   *  demo data uses invented placeholder VINs. */
  vin: string;
  /** Dealer-assigned stock identifier — matches the backend
   *  Copper Canyon seed (CC-{T|S|C|V}-NN). */
  stock_number: string;
  year: number;
  make: string;
  model: string;
  trim: string;
  condition: VehicleCondition;
  drivetrain: string;
  fuel_type: string;
  exterior_color: string | null;
  mileage: number;
  /** Listed price — what the dealership asks. Includes any
   *  standard doc fee per dealership convention. */
  price: number;
  /** Sticker price — always null on a used-only indie lot. */
  msrp: number | null;
  /** Public CDN URL. Unsplash placeholders for the demo. */
  image_url: string;
  /** Vehicle Detail Page URL. Uses an ``example.com`` placeholder
   *  domain — real deployments swap in the dealership's own site. */
  vdp_url: string;
  /** Pre-computed display label for card rendering. */
  display_name: string;
}


export const SAMPLE_INVENTORY: readonly SampleInventoryVehicle[] = [
  // ─── Trucks ──────────────────────────────────────────────────────
  {
    vin: "5TFCZ5AN9EX000101",
    stock_number: "CC-T-01",
    year: 2014,
    make: "Toyota",
    model: "Tacoma",
    trim: "SR5 Double Cab 4x4",
    condition: "used",
    drivetrain: "4x4",
    fuel_type: "Gasoline",
    exterior_color: "Silver Sky Metallic",
    mileage: 118000,
    price: 16995,
    msrp: null,
    image_url: "https://images.unsplash.com/photo-1626668893632-6f3a4466d22f?w=800",
    vdp_url: "https://coppercanyonauto.example.com/inventory/CC-T-01",
    display_name: "2014 Toyota Tacoma SR5 Double Cab 4x4",
  },
  {
    vin: "1FTEW1EP8GKA00202",
    stock_number: "CC-T-02",
    year: 2016,
    make: "Ford",
    model: "F-150",
    trim: "XLT SuperCrew",
    condition: "used",
    drivetrain: "4x4",
    fuel_type: "Gasoline",
    exterior_color: "Shadow Black",
    mileage: 96000,
    price: 18495,
    msrp: null,
    image_url: "https://images.unsplash.com/photo-1583267746897-2cf415887172?w=800",
    vdp_url: "https://coppercanyonauto.example.com/inventory/CC-T-02",
    display_name: "2016 Ford F-150 XLT SuperCrew",
  },
  {
    vin: "1C6RR7LT8LS000303",
    stock_number: "CC-T-06",
    year: 2020,
    make: "Ram",
    model: "1500",
    trim: "Big Horn Crew Cab",
    condition: "used",
    drivetrain: "4x4",
    fuel_type: "Gasoline",
    exterior_color: "Delmonico Red",
    mileage: 58000,
    price: 24995,
    msrp: null,
    image_url: "https://images.unsplash.com/photo-1621997407715-24f2b4d29e42?w=800",
    vdp_url: "https://coppercanyonauto.example.com/inventory/CC-T-06",
    display_name: "2020 Ram 1500 Big Horn Crew Cab",
  },
  // ─── SUVs ────────────────────────────────────────────────────────
  {
    vin: "2T3DFREV3GW000404",
    stock_number: "CC-S-01",
    year: 2016,
    make: "Toyota",
    model: "RAV4",
    trim: "XLE AWD",
    condition: "used",
    drivetrain: "AWD",
    fuel_type: "Gasoline",
    exterior_color: "Magnetic Gray Metallic",
    mileage: 88000,
    price: 14995,
    msrp: null,
    image_url: "https://images.unsplash.com/photo-1533106497176-45ae19e68ba2?w=800",
    vdp_url: "https://coppercanyonauto.example.com/inventory/CC-S-01",
    display_name: "2016 Toyota RAV4 XLE AWD",
  },
  {
    vin: "5J6RW2H88JL000505",
    stock_number: "CC-S-02",
    year: 2018,
    make: "Honda",
    model: "CR-V",
    trim: "EX AWD",
    condition: "used",
    drivetrain: "AWD",
    fuel_type: "Gasoline",
    exterior_color: "Modern Steel Metallic",
    mileage: 74000,
    price: 16995,
    msrp: null,
    image_url: "https://images.unsplash.com/photo-1560958089-b8a1929cea89?w=800",
    vdp_url: "https://coppercanyonauto.example.com/inventory/CC-S-02",
    display_name: "2018 Honda CR-V EX AWD",
  },
  {
    vin: "1C4BJWDG3FL000606",
    stock_number: "CC-S-06",
    year: 2015,
    make: "Jeep",
    model: "Wrangler",
    trim: "Sport 4x4 4-Door",
    condition: "used",
    drivetrain: "4x4",
    fuel_type: "Gasoline",
    exterior_color: "Firecracker Red",
    mileage: 102000,
    price: 17495,
    msrp: null,
    image_url: "https://images.unsplash.com/photo-1533507203900-0a5b4c9ecb32?w=800",
    vdp_url: "https://coppercanyonauto.example.com/inventory/CC-S-06",
    display_name: "2015 Jeep Wrangler Sport 4x4 4-Door",
  },
  {
    vin: "5TDBZRFH8LS000707",
    stock_number: "CC-S-08",
    year: 2020,
    make: "Toyota",
    model: "Highlander",
    trim: "LE AWD",
    condition: "used",
    drivetrain: "AWD",
    fuel_type: "Gasoline",
    exterior_color: "Blueprint",
    mileage: 55000,
    price: 23995,
    msrp: null,
    image_url: "https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=800",
    vdp_url: "https://coppercanyonauto.example.com/inventory/CC-S-08",
    display_name: "2020 Toyota Highlander LE AWD",
  },
  {
    vin: "5FNYF6H51GB000808",
    stock_number: "CC-S-09",
    year: 2016,
    make: "Honda",
    model: "Pilot",
    trim: "EX 8-Passenger",
    condition: "used",
    drivetrain: "AWD",
    fuel_type: "Gasoline",
    exterior_color: "White Diamond Pearl",
    mileage: 89000,
    price: 17995,
    msrp: null,
    image_url: "https://images.unsplash.com/photo-1502877338535-766e1452684a?w=800",
    vdp_url: "https://coppercanyonauto.example.com/inventory/CC-S-09",
    display_name: "2016 Honda Pilot EX 8-Passenger",
  },
  // ─── Cars ────────────────────────────────────────────────────────
  {
    vin: "2HGFC2F58HH000909",
    stock_number: "CC-C-02",
    year: 2017,
    make: "Honda",
    model: "Civic",
    trim: "LX Sedan",
    condition: "used",
    drivetrain: "FWD",
    fuel_type: "Gasoline",
    exterior_color: "Aegean Blue Metallic",
    mileage: 85000,
    price: 12495,
    msrp: null,
    image_url: "https://images.unsplash.com/photo-1590362891991-f776e747a588?w=800",
    vdp_url: "https://coppercanyonauto.example.com/inventory/CC-C-02",
    display_name: "2017 Honda Civic LX Sedan",
  },
  {
    vin: "5YFEPRAE8KP001010",
    stock_number: "CC-C-08",
    year: 2019,
    make: "Toyota",
    model: "Corolla",
    trim: "LE Sedan",
    condition: "used",
    drivetrain: "FWD",
    fuel_type: "Gasoline",
    exterior_color: "Classic Silver Metallic",
    mileage: 66000,
    price: 13795,
    msrp: null,
    image_url: "https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?w=800",
    vdp_url: "https://coppercanyonauto.example.com/inventory/CC-C-08",
    display_name: "2019 Toyota Corolla LE Sedan",
  },
  // ─── Vans ────────────────────────────────────────────────────────
  {
    vin: "5TDKK3DC8FS001111",
    stock_number: "CC-V-02",
    year: 2015,
    make: "Toyota",
    model: "Sienna",
    trim: "LE Minivan",
    condition: "used",
    drivetrain: "FWD",
    fuel_type: "Gasoline",
    exterior_color: "Predawn Gray Mica",
    mileage: 118000,
    price: 12495,
    msrp: null,
    image_url: "https://images.unsplash.com/photo-1601914247720-d33c9a5b2ef2?w=800",
    vdp_url: "https://coppercanyonauto.example.com/inventory/CC-V-02",
    display_name: "2015 Toyota Sienna LE Minivan",
  },
  {
    vin: "2C4RC1BG8JR001212",
    stock_number: "CC-V-03",
    year: 2018,
    make: "Chrysler",
    model: "Pacifica",
    trim: "Touring Minivan",
    condition: "used",
    drivetrain: "FWD",
    fuel_type: "Gasoline",
    exterior_color: "Billet Silver Metallic",
    mileage: 78000,
    price: 16995,
    msrp: null,
    image_url: "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=800",
    vdp_url: "https://coppercanyonauto.example.com/inventory/CC-V-03",
    display_name: "2018 Chrysler Pacifica Touring Minivan",
  },
];

/** Base URL for the "Browse full inventory" CTA. Real deployments
 *  point this at the dealership's live inventory page. */
export const SAMPLE_INVENTORY_HOMEPAGE_URL =
  "https://coppercanyonauto.example.com/inventory/";

/** Date the sample dataset was last refreshed. Displayed in the
 *  demo footer / inventory-preview page so viewers know they're
 *  looking at a static snapshot rather than a live feed. */
export const SAMPLE_INVENTORY_CAPTURED_AT = "2026-07-31";
