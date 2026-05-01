// Frontend-only message parser for the AI Sales Assistant.
//
// Splits an assistant reply into intro / vehicles[] / explanation / question
// so the chat bubble can render structured cards instead of one giant text
// block. Backend logic is unchanged — this is a presentation-layer fix.
//
// Detection strategy:
// - A "vehicle line" is any line that contains "Stock #" (case-insensitive),
//   typically formatted by the backend as one of:
//     "- 2025 Ford F-150 XLT (Stock #FF-2025-001) at $62,995, est ~$717/mo"
//     "1. 2014 Ford Fusion SE | Stock #FF-USED-201 | $11,995"
//     "the 2018 Ford Escape SE FWD (Stock #FF-USED-301, $17,995)"
// - Lines BEFORE the first vehicle line → intro.
// - Lines AFTER each vehicle line that LOOK LIKE inventory-detail bullets
//   (Price/Mileage/Term/etc.) get ABSORBED into that vehicle entry — the
//   card already shows those facts, so duplicating them in the explanation
//   reads as a wall of redundant text.
// - Whatever survives after the last vehicle's absorbed block → trailing
//   block, then split into explanation + a single trailing question.
// - If there are no vehicle lines but a trailing question exists, the
//   parser still returns a structured shape AND tries to promote a short
//   opening paragraph to ``intro`` so the bubble reads as
//   intro / explanation / question instead of one wall.
// - If the parser can't make any progress (no vehicles, no question),
//   it returns ``null`` and the caller falls back to the raw text.
//
// The parser deliberately tolerates messy inputs. It never throws.

export interface ParsedVehicle {
  /** Stock number captured verbatim from the line (without the leading "#"). */
  stock_number: string;
  /** Year if a 19xx/20xx token is present in the line. */
  year: string | null;
  /** First "$X,XXX" price in the line, comma-stripped. */
  price: string | null;
  /** Original line as written, with leading bullet/list markers stripped. */
  display_text: string;
  /** Original raw line (kept for debugging / tooltip). */
  raw: string;
}

export interface ParsedAssistantMessage {
  intro: string;
  vehicles: ParsedVehicle[];
  explanation: string;
  question: string | null;
}

const STOCK_RE = /Stock\s*#\s*([A-Z0-9][A-Z0-9-]*)/i;
const YEAR_RE = /\b(?:19|20)\d{2}\b/;
const PRICE_RE = /\$\s*([\d,]+(?:\.\d{2})?)/;
const LIST_PREFIX_RE = /^[\s\-•·*\d.)]+/;

// Phase 8s/UX — lines that look like duplicated inventory-detail factoids
// the LLM emits right after a vehicle line. The card already shows the
// price, payment, condition, mileage, and drivetrain, so absorbing these
// removes the duplicate-bullet wall the manager was seeing.
//
// Two complementary detectors:
//
// 1. ``FACTOID_LINE_RE`` — strict ``Key: value`` shape with a known field
//    keyword. Catches "* Price: $17,995" and "Estimated monthly payment
//    (W.A.C.): $349/mo".
// 2. ``SHORT_BULLET_RE`` + length/punctuation guard (see ``isAbsorbable``)
//    — catches the common Ollama output "* Used with 73,500 miles" or
//    "* $26,995" where the LLM uses bullets but skips the colon. Short
//    bullets without terminal punctuation are almost always factoids;
//    long bullets or ones ending in ``.``/``!``/``?`` are prose and stay
//    in ``explanation``.
const FACTOID_LINE_RE =
  /^\s*[*\-•·]?\s*(price|stock|year|make|model|trim|mileage|condition|msrp|down(?:\s*payment)?|term|engine|drivetrain|transmission|fuel(?:\s*type)?|exterior|interior|color|estimated|est|monthly|payment|body)\b[^:\n]{0,80}:/i;

const SHORT_BULLET_RE = /^\s*[*\-•·]\s/;
const SHORT_BULLET_MAX_CHARS = 60;

function isAbsorbable(line: string): boolean {
  if (FACTOID_LINE_RE.test(line)) return true;
  if (!SHORT_BULLET_RE.test(line)) return false;
  const trimmed = line.trim();
  if (trimmed.length > SHORT_BULLET_MAX_CHARS) return false;
  const lastChar = trimmed.slice(-1);
  if (lastChar === "." || lastChar === "!" || lastChar === "?") return false;
  return true;
}

const PARAGRAPH_BREAK_RE = /^([\s\S]*?)\n\s*\n([\s\S]*)$/;
const INTRO_MAX_CHARS = 240;

function parseVehicleLine(line: string): ParsedVehicle | null {
  const stockMatch = STOCK_RE.exec(line);
  if (!stockMatch) return null;
  const yearMatch = YEAR_RE.exec(line);
  const priceMatch = PRICE_RE.exec(line);
  const display = line.replace(LIST_PREFIX_RE, "").trim();
  return {
    stock_number: stockMatch[1],
    year: yearMatch ? yearMatch[0] : null,
    price: priceMatch ? priceMatch[1].replace(/,/g, "") : null,
    display_text: display,
    raw: line,
  };
}

/**
 * Walk forward from a vehicle line, absorbing detail-bullet lines and
 * blank lines that visually belong to that vehicle's entry. Stops at the
 * next vehicle line OR a non-factoid prose line. Returns the set of line
 * indices to absorb (always includes ``startIdx`` itself).
 */
function absorbDetailLines(lines: string[], startIdx: number): Set<number> {
  const absorbed = new Set<number>([startIdx]);
  for (let i = startIdx + 1; i < lines.length; i++) {
    const line = lines[i];
    // A new vehicle line ends this vehicle's detail block.
    if (STOCK_RE.test(line)) break;
    // Blank lines between bullets stay with the vehicle.
    if (line.trim() === "") {
      absorbed.add(i);
      continue;
    }
    // Factoid bullets and short un-punctuated bullets duplicate card
    // data — absorb. See ``isAbsorbable`` for the heuristic.
    if (isAbsorbable(line)) {
      absorbed.add(i);
      continue;
    }
    // Anything else (descriptive prose) belongs in the explanation.
    break;
  }
  return absorbed;
}

/**
 * Split a free-form text block into ``{ body, question }``. The "question"
 * is the last sentence iff it ends with "?". Multi-question replies are
 * collapsed: only the trailing one survives, so the chat bubble renders
 * exactly one question — matching the dealership voice rule that the
 * backend system prompt already enforces.
 */
function splitTrailingQuestion(text: string): {
  body: string;
  question: string | null;
} {
  const trimmed = text.trim();
  if (!trimmed) return { body: "", question: null };
  // Sentence-ish split: punctuation followed by whitespace.
  const parts = trimmed.split(/(?<=[.!?])\s+/);
  if (parts.length === 0) return { body: trimmed, question: null };
  const last = parts[parts.length - 1].trim();
  if (last.endsWith("?")) {
    const body = parts.slice(0, -1).join(" ").trim();
    return { body, question: last };
  }
  return { body: trimmed, question: null };
}

/**
 * Promote the first paragraph (separated by a blank line) to ``intro``
 * when it's short enough to read as a greeting/lead-in. Long openings
 * stay intact in ``body`` so we don't accidentally lop off an
 * explanation that happens to start with a complete sentence.
 */
function splitFirstParagraph(text: string): { intro: string; body: string } {
  const trimmed = text.trim();
  if (!trimmed) return { intro: "", body: "" };
  const m = trimmed.match(PARAGRAPH_BREAK_RE);
  if (!m) return { intro: "", body: trimmed };
  const intro = m[1].trim();
  const body = m[2].trim();
  if (!intro || intro.length > INTRO_MAX_CHARS) {
    return { intro: "", body: trimmed };
  }
  return { intro, body };
}

/**
 * Parse an assistant message. Returns ``null`` when the parser can't
 * find anything worth structuring (no vehicle lines, no trailing
 * question) — caller renders the original text in that case.
 */
export function parseAssistantMessage(
  text: string,
): ParsedAssistantMessage | null {
  if (!text) return null;
  const lines = text.split("\n");

  const vehicleIndices: number[] = [];
  for (let i = 0; i < lines.length; i++) {
    if (STOCK_RE.test(lines[i])) {
      vehicleIndices.push(i);
    }
  }

  // No vehicle lines — try the simpler "explanation + question" split so
  // single-paragraph replies still get the question on its own line. Also
  // promote a short first paragraph to ``intro`` (Fix 3) when present.
  //
  // Order matters: splitFirstParagraph runs BEFORE splitTrailingQuestion
  // because the former reads blank-line breaks and the latter joins
  // sentences with spaces (which would obliterate the breaks).
  if (vehicleIndices.length === 0) {
    const para = splitFirstParagraph(text);
    const split = splitTrailingQuestion(para.body);
    if (!split.question) {
      // Nothing useful to do — let the caller fall back to raw text.
      return null;
    }
    return {
      intro: para.intro,
      vehicles: [],
      explanation: split.body,
      question: split.question,
    };
  }

  const firstVehicleIdx = vehicleIndices[0];

  // Walk forward from each vehicle line and collect lines that visually
  // belong to it (detail bullets + their inline blank lines). Anything
  // not absorbed here ends up in the trailing block (explanation/question).
  const absorbed = new Set<number>();
  for (const idx of vehicleIndices) {
    for (const a of absorbDetailLines(lines, idx)) {
      absorbed.add(a);
    }
  }

  const introLines = lines.slice(0, firstVehicleIdx);
  // Trailing = everything after the first vehicle line that wasn't
  // absorbed by some vehicle's detail walk.
  const trailingLines: string[] = [];
  for (let i = firstVehicleIdx + 1; i < lines.length; i++) {
    if (!absorbed.has(i)) trailingLines.push(lines[i]);
  }

  const vehicles: ParsedVehicle[] = [];
  for (const idx of vehicleIndices) {
    const v = parseVehicleLine(lines[idx]);
    if (v) vehicles.push(v);
  }

  if (vehicles.length === 0) {
    // Defensive: the indices said "Stock #" was present but the regex
    // for parsing failed. Bail to fallback rather than rendering an
    // empty card grid.
    return null;
  }

  const intro = introLines.join("\n").trim();
  const trailing = trailingLines.join("\n").trim();
  const split = splitTrailingQuestion(trailing);

  // Rescue path: Ollama sometimes crams everything (vehicle line +
  // explanation + question) onto a single pipe-delimited line. The
  // card still renders cleanly via the matched Vehicle, but the
  // question is otherwise lost inside ``display_text``. When the
  // structured trailing block didn't yield a question, re-scan the
  // ORIGINAL text for a trailing ``?`` and surface it as the question
  // pill. We deliberately don't touch ``explanation`` here — that
  // would risk duplicating the inventory text that the card already
  // shows.
  let question = split.question;
  if (question === null) {
    const fallback = splitTrailingQuestion(text);
    if (fallback.question) {
      question = fallback.question;
    }
  }

  return {
    intro,
    vehicles,
    explanation: split.body,
    question,
  };
}
