// The five agents as an original, Avengers-inspired hero squad.
// Every drawing is our own SVG: no Marvel names, logos, or artwork.
import type { JSX } from "react";
import type { AgentName, Mood } from "./types";

export interface Hero {
  agent: AgentName;
  name: string;
  role: string;
  tagline: string;
  color: string; // main suit color
  accent: string; // trim / glow
  emoji: string;
}

export const HEROES: Record<AgentName, Hero> = {
  boss: {
    agent: "boss",
    name: "Captain Yale",
    role: "Boss",
    tagline: "Plans the mission, makes the call, guards the budget.",
    color: "#00356b",
    accent: "#286dc0",
    emoji: "🛡️",
  },
  inventory: {
    agent: "inventory",
    name: "Iron Stock",
    role: "Inventory",
    tagline: "Scans every shelf, size, and vendor.",
    color: "#b3261e",
    accent: "#f2b134",
    emoji: "📦",
  },
  accounting: {
    agent: "accounting",
    name: "Doctor Margin",
    role: "Accounting",
    tagline: "Sees every dollar's future. Files the requests.",
    color: "#1f6f78",
    accent: "#7fe0c8",
    emoji: "💰",
  },
  facilities: {
    agent: "facilities",
    name: "The Fortress",
    role: "Facilities",
    tagline: "Holds the building up. Never late on rent.",
    color: "#3f7d3a",
    accent: "#f5c542",
    emoji: "🏛️",
  },
  customer_service: {
    agent: "customer_service",
    name: "Friendly Neighbor",
    role: "Customer Service",
    tagline: "The customer's voice on the team.",
    color: "#d9485f",
    accent: "#2c4a9a",
    emoji: "💬",
  },
};

export const HERO_ORDER: AgentName[] = ["boss", "inventory", "accounting", "facilities", "customer_service"];

export const heroName = (agent?: string) => (agent && agent in HEROES ? HEROES[agent as AgentName].name : agent ?? "Team");

// ---------------------------------------------------------------------------
// Faces
// ---------------------------------------------------------------------------

function Eyes({ mood, y, color = "#1d2733" }: { mood: Mood; y: number; color?: string }) {
  if (mood === "happy" || mood === "celebrate") {
    return (
      <g stroke={color} strokeWidth={3} fill="none" strokeLinecap="round">
        <path d={`M41 ${y + 2} q5 -6 10 0`} />
        <path d={`M69 ${y + 2} q5 -6 10 0`} />
      </g>
    );
  }
  if (mood === "worried" || mood === "sad") {
    return (
      <g fill={color}>
        <ellipse cx={46} cy={y + 1} rx={3.2} ry={4} />
        <ellipse cx={74} cy={y + 1} rx={3.2} ry={4} />
        <path d={`M39 ${y - 8} l12 4`} stroke={color} strokeWidth={2.5} strokeLinecap="round" />
        <path d={`M81 ${y - 8} l-12 4`} stroke={color} strokeWidth={2.5} strokeLinecap="round" />
      </g>
    );
  }
  if (mood === "thinking") {
    return (
      <g fill={color}>
        <circle cx={48} cy={y - 2} r={3.4} />
        <circle cx={76} cy={y - 2} r={3.4} />
        <path d={`M40 ${y - 9} l12 -2`} stroke={color} strokeWidth={2.5} strokeLinecap="round" />
      </g>
    );
  }
  return (
    <g fill={color}>
      <circle cx={46} cy={y} r={3.6} />
      <circle cx={74} cy={y} r={3.6} />
    </g>
  );
}

function Mouth({ mood, y }: { mood: Mood; y: number }) {
  const s = { stroke: "#1d2733", strokeWidth: 3, fill: "none", strokeLinecap: "round" as const };
  switch (mood) {
    case "happy":
      return <path d={`M48 ${y} q12 10 24 0`} {...s} />;
    case "celebrate":
      return <path d={`M47 ${y - 1} q13 15 26 0 z`} fill="#7a1c1c" stroke="#1d2733" strokeWidth={2.5} />;
    case "worried":
      return <path d={`M49 ${y + 4} q11 -7 22 0`} {...s} />;
    case "sad":
      return <path d={`M48 ${y + 5} q12 -9 24 0`} {...s} />;
    case "thinking":
      return <path d={`M52 ${y + 2} h14`} {...s} />;
    default:
      return <path d={`M50 ${y} q10 5 20 0`} {...s} />;
  }
}

function Extras({ mood }: { mood: Mood }) {
  if (mood === "worried" || mood === "sad")
    return <path d="M93 44 q5 9 0 13 q-5 -4 0 -13z" fill="#7cc6ff" stroke="#3b82c4" strokeWidth={1} />;
  if (mood === "thinking")
    return (
      <g fill="#9aa8bb">
        <circle cx={97} cy={30} r={3} />
        <circle cx={104} cy={22} r={4} />
        <circle cx={112} cy={12} r={5} />
      </g>
    );
  if (mood === "celebrate")
    return (
      <g fill="#f2b134">
        <path d="M14 22 l3 7 7 1 -5 5 1 7 -6 -4 -6 4 1 -7 -5 -5 7 -1z" />
        <path d="M104 18 l2 5 5 1 -4 3 1 5 -4 -3 -4 3 1 -5 -4 -3 5 -1z" />
      </g>
    );
  return null;
}

// ---------------------------------------------------------------------------
// Suits (head + headgear + emblem). viewBox 0 0 120 120
// ---------------------------------------------------------------------------

const SKIN = "#f3c9a5";

function CaptainYale({ mood }: { mood: Mood }) {
  return (
    <>
      <path d="M22 120 q0 -26 38 -30 q38 4 38 30z" fill="#00356b" />
      <path d="M50 92 h20 l-10 12z" fill="#fff" />
      <circle cx={60} cy={56} r={30} fill={SKIN} />
      {/* helmet */}
      <path d="M29 56 q0 -34 31 -34 q31 0 31 34 v-6 q-3 -8 -10 -10 h-42 q-7 2 -10 10z" fill="#00356b" />
      <path d="M31 44 h58 v8 h-58z" fill="#00356b" />
      <circle cx={60} cy={33} r={8} fill="#fff" />
      <text x={60} y={38} textAnchor="middle" fontFamily="Georgia, serif" fontWeight={700} fontSize={12} fill="#00356b">Y</text>
      <Eyes mood={mood} y={60} />
      <Mouth mood={mood} y={72} />
      {/* shield */}
      <g transform="translate(88 86)">
        <circle r={17} fill="#00356b" />
        <circle r={12.5} fill="#fff" />
        <circle r={8.5} fill="#286dc0" />
        <text y={4} textAnchor="middle" fontFamily="Georgia, serif" fontWeight={700} fontSize={11} fill="#fff">Y</text>
      </g>
    </>
  );
}

function IronStock({ mood }: { mood: Mood }) {
  const eye = mood === "worried" || mood === "sad" ? "#ffb4a8" : "#fff6c9";
  return (
    <>
      <path d="M22 120 q0 -26 38 -30 q38 4 38 30z" fill="#b3261e" />
      <circle cx={60} cy={103} r={7} fill="#fff6c9" stroke="#f2b134" strokeWidth={2} />
      <path d="M30 54 q0 -32 30 -32 q30 0 30 32 q0 26 -30 32 q-30 -6 -30 -32z" fill="#b3261e" />
      {/* faceplate */}
      <path d="M38 50 q0 -14 22 -14 q22 0 22 14 v14 q0 14 -22 18 q-22 -4 -22 -18z" fill="#f2b134" />
      <g fill={eye} stroke="#8a5b00" strokeWidth={1}>
        {mood === "happy" || mood === "celebrate" ? (
          <>
            <path d="M42 56 q6 -6 12 0 q-6 -2 -12 0z" />
            <path d="M66 56 q6 -6 12 0 q-6 -2 -12 0z" />
          </>
        ) : (
          <>
            <path d={mood === "worried" || mood === "sad" ? "M42 54 l12 3 v3 l-12 -2z" : "M42 55 h12 l-1 4 h-10z"} />
            <path d={mood === "worried" || mood === "sad" ? "M78 54 l-12 3 v3 l12 -2z" : "M66 55 h12 l-1 4 h-10z"} />
          </>
        )}
      </g>
      <Mouth mood={mood} y={71} />
      {/* box emblem */}
      <g transform="translate(86 92)">
        <rect x={-9} y={-8} width={18} height={15} fill="#f2b134" stroke="#8a5b00" strokeWidth={1.5} />
        <path d="M-9 -3 h18 M0 -8 v15" stroke="#8a5b00" strokeWidth={1.5} />
      </g>
    </>
  );
}

function DoctorMargin({ mood }: { mood: Mood }) {
  return (
    <>
      <path d="M14 120 q2 -34 30 -38 l16 10 l16 -10 q28 4 30 38z" fill="#7a2230" />
      <path d="M26 120 q0 -24 34 -28 q34 4 34 28z" fill="#1f6f78" />
      <path d="M30 86 l-8 -20 l18 14z M90 86 l8 -20 l-18 14z" fill="#7a2230" />
      <circle cx={60} cy={56} r={29} fill={SKIN} />
      <path d="M31 52 q2 -30 29 -30 q27 0 29 30 q-6 -14 -16 -16 q-4 6 -13 6 q-9 0 -13 -6 q-10 2 -16 16z" fill="#2d2a2a" />
      <path d="M33 46 q2 -8 8 -10" stroke="#c9c9c9" strokeWidth={3} fill="none" />
      <Eyes mood={mood} y={58} />
      <path d="M52 78 q8 8 16 0 v4 q-8 8 -16 0z" fill="#2d2a2a" />
      <Mouth mood={mood} y={71} />
      {/* amulet */}
      <g transform="translate(60 102)">
        <circle r={9} fill="#7fe0c8" stroke="#f2b134" strokeWidth={2.5} />
        <text y={4.5} textAnchor="middle" fontSize={12} fontWeight={700} fill="#0d4a50">$</text>
      </g>
    </>
  );
}

function TheFortress({ mood }: { mood: Mood }) {
  return (
    <>
      <path d="M8 120 q0 -32 52 -36 q52 4 52 36z" fill="#4f9a49" />
      <path d="M8 120 q4 -22 26 -30 l-4 30z M112 120 q-4 -22 -26 -30 l4 30z" fill="#3f7d3a" />
      <rect x={34} y={96} width={52} height={24} fill="#6b4ea0" />
      <circle cx={60} cy={58} r={31} fill="#79b86f" />
      <path d="M34 62 q-3 -18 4 -24 M86 62 q3 -18 -4 -24" stroke="#5d9654" strokeWidth={3} fill="none" />
      {/* hard hat */}
      <path d="M28 44 q2 -24 32 -24 q30 0 32 24z" fill="#f5c542" />
      <rect x={24} y={42} width={72} height={6} rx={3} fill="#e0a92a" />
      <rect x={56} y={22} width={8} height={20} fill="#e0a92a" />
      <path d="M40 56 l10 3 M80 56 l-10 3" stroke="#2c3a2a" strokeWidth={3} strokeLinecap="round" />
      <Eyes mood={mood} y={63} color="#1f2a1d" />
      <Mouth mood={mood} y={77} />
      {/* brick emblem */}
      <g transform="translate(60 106)" stroke="#f5c542" strokeWidth={1.4} fill="#a5532e">
        <rect x={-11} y={-6} width={10} height={5} />
        <rect x={1} y={-6} width={10} height={5} />
        <rect x={-5} y={0} width={10} height={5} />
      </g>
    </>
  );
}

function FriendlyNeighbor({ mood }: { mood: Mood }) {
  const happy = mood === "happy" || mood === "celebrate";
  const sad = mood === "worried" || mood === "sad";
  return (
    <>
      <path d="M22 120 q0 -26 38 -30 q38 4 38 30z" fill="#2c4a9a" />
      <path d="M40 120 q4 -22 20 -26 q16 4 20 26z" fill="#d9485f" />
      <circle cx={60} cy={56} r={30} fill="#d9485f" />
      {/* web lines */}
      <g stroke="#8f2234" strokeWidth={1} fill="none" opacity={0.7}>
        <path d="M60 26 v60 M30 56 h60 M39 35 l42 42 M81 35 l-42 42" />
        <circle cx={60} cy={56} r={12} />
        <circle cx={60} cy={56} r={22} />
      </g>
      {/* mask eyes */}
      <g fill="#fff" stroke="#1d2733" strokeWidth={2.5}>
        {happy ? (
          <>
            <path d="M37 54 q9 -12 18 0 q-9 -4 -18 0z" />
            <path d="M65 54 q9 -12 18 0 q-9 -4 -18 0z" />
          </>
        ) : sad ? (
          <>
            <path d="M37 48 q12 2 17 10 q-12 4 -17 -10z" />
            <path d="M83 48 q-12 2 -17 10 q12 4 17 -10z" />
          </>
        ) : (
          <>
            <path d="M36 48 q12 -2 18 10 q-13 6 -18 -10z" />
            <path d="M84 48 q-12 -2 -18 10 q13 6 18 -10z" />
          </>
        )}
      </g>
      <Mouth mood={mood} y={73} />
      {/* heart-bubble emblem */}
      <g transform="translate(88 94)">
        <path d="M-11 -9 h22 a4 4 0 0 1 4 4 v10 a4 4 0 0 1 -4 4 h-12 l-6 6 v-6 h-4 a4 4 0 0 1 -4 -4 v-10 a4 4 0 0 1 4 -4z" fill="#fff" stroke="#2c4a9a" strokeWidth={1.5} />
        <path d="M0 4 l-5 -5 a3 3 0 0 1 5 -3 a3 3 0 0 1 5 3z" fill="#d9485f" />
      </g>
    </>
  );
}

const SUITS: Record<AgentName, (p: { mood: Mood }) => JSX.Element> = {
  boss: CaptainYale,
  inventory: IronStock,
  accounting: DoctorMargin,
  facilities: TheFortress,
  customer_service: FriendlyNeighbor,
};

export function Avatar({ agent, mood, size = 96 }: { agent: AgentName; mood: Mood; size?: number }) {
  const Suit = SUITS[agent];
  return (
    <svg viewBox="0 0 120 120" width={size} height={size} role="img" aria-label={`${HEROES[agent].name}, ${mood}`}>
      <Suit mood={mood} />
      <Extras mood={mood} />
    </svg>
  );
}
