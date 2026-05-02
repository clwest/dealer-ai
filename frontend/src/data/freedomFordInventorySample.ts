// SESSION_014 — demo / sample inventory snapshot.
//
// Captured via Playwright from samsfreedomford.com on 2026-05-02. This
// is **sample data for UI/demo realism only**. It is NOT the
// production inventory pipeline; the Live Assistant page still fetches
// real inventory through the backend `start_chat` / `send_message`
// APIs and is not affected by this file.
//
// Long-term, this surface will be fed by a CRM/DMS feed integration.
// When that lands, delete this file and migrate consumers to the live
// data source — the shape on the wire will look different.
//
// Rules followed during capture:
//   - Public marketing pages only (the dealer publishes these).
//   - Two pages visited: /inventory/new-vehicles/ and
//     /inventory/used-vehicles/.
//   - Image URLs only — no images downloaded into the repo.
//   - Sample size capped at ~18 vehicles, curated for visual variety
//     (new + used, multiple body styles, multiple brands).
//   - No login, no rate-pushing, no scrolling beyond what's needed
//     to trigger the lazy-load already exposed to humans.

export type VehicleCondition = "new" | "used" | "certified";

export interface FreedomFordSampleVehicle {
  /** 17-char VIN — used as a stable key. */
  vin: string;
  /** Dealer-assigned stock identifier as printed on the public listing. */
  stock_number: string;
  year: number;
  make: string;
  model: string;
  trim: string;
  condition: VehicleCondition;
  /** Free-form: "AWD", "4WD", "RWD", "FWD", "4×4", etc. */
  drivetrain: string;
  /** Free-form: "Gasoline", "Hybrid", "Electric", "Diesel". */
  fuel_type: string;
  exterior_color: string | null;
  /** 0 for new vehicles. */
  mileage: number;
  /** "Freedom Price" as displayed on the listing — what the dealer
   *  asks. Includes doc fee per the public site's pricing breakdown. */
  price: number;
  /** Sticker price; only present on new vehicles. */
  msrp: number | null;
  /** Public CDN URL. Protocol-relative on the source page; we
   *  prepend `https:` here so consumers don't have to. */
  image_url: string;
  /** Vehicle Detail Page on samsfreedomford.com (used for "View
   *  on dealer site" deep-links from the demo page). */
  vdp_url: string;
  /** Pre-computed for card rendering convenience. */
  display_name: string;
}

export const FREEDOM_FORD_SAMPLE_INVENTORY: readonly FreedomFordSampleVehicle[] =
  [
    // ─── New ──────────────────────────────────────────────────────────
    {
      vin: "3FTTW8BA8SRB66401",
      stock_number: "SRB66401",
      year: 2025,
      make: "Ford",
      model: "Maverick",
      trim: "XL AWD SuperCrew",
      condition: "new",
      drivetrain: "AWD",
      fuel_type: "Gasoline",
      exterior_color: "Desert Sand",
      mileage: 0,
      price: 31163,
      msrp: 31165,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/298504606",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/3FTTW8BA8SRB66401/2025-Ford-Maverick-XL-Mcalester-OK/",
      display_name: "2025 Ford Maverick XL AWD SuperCrew",
    },
    {
      vin: "3FTTW8A35TRA65790",
      stock_number: "TRA65790",
      year: 2026,
      make: "Ford",
      model: "Maverick",
      trim: "XL FWD SuperCrew",
      condition: "new",
      drivetrain: "FWD",
      fuel_type: "Hybrid",
      exterior_color: "Light Blue",
      mileage: 0,
      price: 31319,
      msrp: 30730,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/309644466",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/3FTTW8A35TRA65790/2026-Ford-Maverick-XL-Mcalester-OK/",
      display_name: "2026 Ford Maverick XL FWD SuperCrew (Hybrid)",
    },
    {
      vin: "3FTTW8HA2TRA42052",
      stock_number: "TRA42052",
      year: 2026,
      make: "Ford",
      model: "Maverick",
      trim: "XLT FWD SuperCrew",
      condition: "new",
      drivetrain: "FWD",
      fuel_type: "Gasoline",
      exterior_color: "White Metallic",
      mileage: 0,
      price: 32044,
      msrp: 31455,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/306670072",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/3FTTW8HA2TRA42052/2026-Ford-Maverick-XLT-Mcalester-OK/",
      display_name: "2026 Ford Maverick XLT FWD SuperCrew",
    },
    {
      vin: "3FTTW8A35TRA45913",
      stock_number: "TRA45913",
      year: 2026,
      make: "Ford",
      model: "Maverick",
      trim: "XL FWD SuperCrew",
      condition: "new",
      drivetrain: "FWD",
      fuel_type: "Hybrid",
      exterior_color: "Orange Fury Metallic Tri-Coat",
      mileage: 0,
      price: 32159,
      msrp: 31570,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/308227630",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/3FTTW8A35TRA45913/2026-Ford-Maverick-XL-Mcalester-OK/",
      display_name: "2026 Ford Maverick XL FWD SuperCrew (Hybrid)",
    },
    {
      vin: "3FTTW8BA9TRA52800",
      stock_number: "TRA52800",
      year: 2026,
      make: "Ford",
      model: "Maverick",
      trim: "XL AWD SuperCrew",
      condition: "new",
      drivetrain: "AWD",
      fuel_type: "Gasoline",
      exterior_color: null,
      mileage: 0,
      price: 32309,
      msrp: 31720,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/310901204",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/3FTTW8BA9TRA52800/2026-Ford-Maverick-XL-Mcalester-OK/",
      display_name: "2026 Ford Maverick XL AWD SuperCrew",
    },
    {
      vin: "3FMCR9BN8TRE48339",
      stock_number: "TRE48339",
      year: 2026,
      make: "Ford",
      model: "Bronco Sport",
      trim: "Big Bend 4×4",
      condition: "new",
      drivetrain: "4×4",
      fuel_type: "Gasoline",
      exterior_color: "Oxford White",
      mileage: 0,
      price: 33324,
      msrp: 32735,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/310629271",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/3FMCR9BN8TRE48339/2026-Ford-Bronco_Sport-BIG_Bend-Mcalester-OK/",
      display_name: "2026 Ford Bronco Sport Big Bend 4×4",
    },
    {
      vin: "1FMCU9GN2TUA39401",
      stock_number: "TUA39401",
      year: 2026,
      make: "Ford",
      model: "Escape",
      trim: "Active AWD",
      condition: "new",
      drivetrain: "AWD",
      fuel_type: "Gasoline",
      exterior_color: "Space Silver Metallic",
      mileage: 0,
      price: 33624,
      msrp: 33535,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/301699818",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/1FMCU9GN2TUA39401/2026-Ford-Escape-Active-Mcalester-OK/",
      display_name: "2026 Ford Escape Active AWD",
    },
    {
      vin: "3FTTW8H3XTRA48473",
      stock_number: "TRA48473",
      year: 2026,
      make: "Ford",
      model: "Maverick",
      trim: "XLT FWD SuperCrew",
      condition: "new",
      drivetrain: "FWD",
      fuel_type: "Hybrid",
      exterior_color: "Velocity Blue",
      mileage: 0,
      price: 33879,
      msrp: 33290,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/308227684",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/3FTTW8H3XTRA48473/2026-Ford-Maverick-XLT-Mcalester-OK/",
      display_name: "2026 Ford Maverick XLT FWD SuperCrew (Hybrid)",
    },

    // ─── Used / Certified ─────────────────────────────────────────────
    {
      vin: "1G6AR5SX4H0168496",
      stock_number: "TLE05326C",
      year: 2017,
      make: "Cadillac",
      model: "CTS",
      trim: "2.0L Turbo Luxury",
      condition: "used",
      drivetrain: "RWD",
      fuel_type: "Gasoline",
      exterior_color: "Moonstone Metallic",
      mileage: 66993,
      price: 22176,
      msrp: null,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/72337038",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/1G6AR5SX4H0168496/Used-2017-Cadillac-CTS-2.0L_Turbo_Luxury-_Mcalester-OK/",
      display_name: "2017 Cadillac CTS 2.0L Turbo Luxury",
    },
    {
      vin: "WDDZF6JB8KA532642",
      stock_number: "SWG12419B",
      year: 2019,
      make: "Mercedes-Benz",
      model: "E-Class",
      trim: "E 450 4MATIC®",
      condition: "used",
      drivetrain: "AWD",
      fuel_type: "Gasoline",
      exterior_color: "Black",
      mileage: 95753,
      price: 24323,
      msrp: null,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/311011616",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/WDDZF6JB8KA532642/Used-2019-Mercedes--Benz-E--Class-E_450-_Mcalester-OK/",
      display_name: "2019 Mercedes-Benz E-Class E 450 4MATIC",
    },
    {
      vin: "JM3KFBBL3R0436873",
      stock_number: "R3464",
      year: 2024,
      make: "Mazda",
      model: "CX-5",
      trim: "2.5 S Select Package",
      condition: "used",
      drivetrain: "AWD",
      fuel_type: "Gasoline",
      exterior_color: "Soul Red Crystal Metallic",
      mileage: 40606,
      price: 27439,
      msrp: null,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/307478079",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/JM3KFBBL3R0436873/Used-2024-Mazda-CX--5-2.5_S_Select_Package-_Mcalester-OK/",
      display_name: "2024 Mazda CX-5 2.5 S Select",
    },
    {
      vin: "1FTEW1E55KKE33965",
      stock_number: "TKD74661A",
      year: 2019,
      make: "Ford",
      model: "F-150",
      trim: "XL 4WD SuperCrew 5.5′ Box",
      condition: "used",
      drivetrain: "4WD",
      fuel_type: "Gasoline",
      exterior_color: "Magnetic",
      mileage: 75086,
      price: 28006,
      msrp: null,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/92852713",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/1FTEW1E55KKE33965/Used-2019-Ford-F--150-XL-_Mcalester-OK/",
      display_name: "2019 Ford F-150 XL 4WD SuperCrew",
    },
    {
      vin: "1FTER4FH2NLD31040",
      stock_number: "R3385A",
      year: 2022,
      make: "Ford",
      model: "Ranger",
      trim: "XLT 4WD SuperCrew 5′ Box",
      condition: "used",
      drivetrain: "4WD",
      fuel_type: "Gasoline",
      exterior_color: "Shadow Black",
      mileage: 80643,
      price: 29089,
      msrp: null,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/311010616",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/1FTER4FH2NLD31040/Used-2022-Ford-Ranger-XLT-_Mcalester-OK/",
      display_name: "2022 Ford Ranger XLT 4WD SuperCrew",
    },
    {
      vin: "3FMCR9B66PRD16761",
      stock_number: "R3438",
      year: 2023,
      make: "Ford",
      model: "Bronco Sport",
      trim: "Big Bend 4×4",
      condition: "certified",
      drivetrain: "4×4",
      fuel_type: "Gasoline",
      exterior_color: "Cactus",
      mileage: 36523,
      price: 29539,
      msrp: null,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/303237188",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/3FMCR9B66PRD16761/Used-2023-Ford-Bronco_Sport-BIG_Bend-_Mcalester-OK/",
      display_name: "2023 Ford Bronco Sport Big Bend 4×4 (Certified)",
    },
    {
      vin: "3C4NJDCN7ST513091",
      stock_number: "R3492",
      year: 2025,
      make: "Jeep",
      model: "Compass",
      trim: "Limited 4×4",
      condition: "used",
      drivetrain: "4×4",
      fuel_type: "Gasoline",
      exterior_color: "Silver Zynith Metallic Clearcoat",
      mileage: 42748,
      price: 30014,
      msrp: null,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/309636786",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/3C4NJDCN7ST513091/Used-2025-Jeep-Compass-Limited-_Mcalester-OK/",
      display_name: "2025 Jeep Compass Limited 4×4",
    },
    {
      vin: "3GNKBERSXNS154727",
      stock_number: "R3470A",
      year: 2022,
      make: "Chevrolet",
      model: "Blazer",
      trim: "RS",
      condition: "used",
      drivetrain: "FWD",
      fuel_type: "Gasoline",
      exterior_color: "Nitro Yellow Metallic",
      mileage: 45094,
      price: 30266,
      msrp: null,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/309173437",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/3GNKBERSXNS154727/Used-2022-Chevrolet-Blazer-RS-_Mcalester-OK/",
      display_name: "2022 Chevrolet Blazer RS FWD",
    },
    {
      vin: "3FMCR9B62RRE86263",
      stock_number: "R3477",
      year: 2024,
      make: "Ford",
      model: "Bronco Sport",
      trim: "Big Bend 4×4",
      condition: "certified",
      drivetrain: "4×4",
      fuel_type: "Gasoline",
      exterior_color: "Oxford White",
      mileage: 23172,
      price: 30559,
      msrp: null,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/309637385",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/3FMCR9B62RRE86263/Used-2024-Ford-Bronco_Sport-BIG_Bend-_Mcalester-OK/",
      display_name: "2024 Ford Bronco Sport Big Bend 4×4 (Certified)",
    },
    {
      vin: "5LMCJ1D98NUL29613",
      stock_number: "R3434",
      year: 2022,
      make: "Lincoln",
      model: "Corsair",
      trim: "Standard AWD",
      condition: "used",
      drivetrain: "AWD",
      fuel_type: "Gasoline",
      exterior_color: "Red",
      mileage: 28998,
      price: 32150,
      msrp: null,
      image_url: "https://media-cdn-a5-jazel-tango.jazel-qa.com/media/304254132",
      vdp_url:
        "https://www.samsfreedomford.com/vehicle/5LMCJ1D98NUL29613/Used-2022-Lincoln-Corsair-Standard-_Mcalester-OK/",
      display_name: "2022 Lincoln Corsair Standard AWD",
    },
  ];

export const FREEDOM_FORD_SAMPLE_CAPTURED_AT = "2026-05-02";
export const FREEDOM_FORD_SAMPLE_SOURCE_URL =
  "https://www.samsfreedomford.com/inventory/";
