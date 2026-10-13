// Small sound effects synthesized with the Web Audio API (no audio files). Off by default.
let ctx: AudioContext | null = null;
let enabled = false;

export const sound = {
  get enabled() {
    return enabled;
  },
  set(on: boolean) {
    enabled = on;
    if (on && !ctx) ctx = new AudioContext();
  },
};

function tone(freq: number, start: number, dur: number, type: OscillatorType = "sine", gain = 0.18) {
  if (!ctx) return;
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = type;
  o.frequency.setValueAtTime(freq, ctx.currentTime + start);
  g.gain.setValueAtTime(gain, ctx.currentTime + start);
  g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + dur);
  o.connect(g).connect(ctx.destination);
  o.start(ctx.currentTime + start);
  o.stop(ctx.currentTime + start + dur);
}

function thump(start = 0) {
  if (!ctx) return;
  const len = ctx.sampleRate * 0.25;
  const buf = ctx.createBuffer(1, len, ctx.sampleRate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 4);
  const src = ctx.createBufferSource();
  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.value = 600;
  const g = ctx.createGain();
  g.gain.value = 0.9;
  src.buffer = buf;
  src.connect(filter).connect(g).connect(ctx.destination);
  src.start(ctx.currentTime + start);
  tone(70, start, 0.25, "sine", 0.5);
}

export function play(name: "assemble" | "stamp" | "cash" | "deny" | "done") {
  if (!enabled || !ctx) return;
  if (ctx.state === "suspended") void ctx.resume();
  switch (name) {
    case "assemble":
      [392, 523, 659, 784].forEach((f, i) => tone(f, i * 0.09, 0.35, "triangle", 0.15));
      break;
    case "stamp":
      thump();
      break;
    case "cash":
      tone(1318, 0, 0.12, "square", 0.08);
      tone(1760, 0.1, 0.35, "square", 0.08);
      break;
    case "deny":
      thump();
      tone(150, 0.05, 0.4, "sawtooth", 0.12);
      break;
    case "done":
      [523, 659, 784, 1046].forEach((f, i) => tone(f, i * 0.12, 0.5, "triangle", 0.14));
      break;
  }
}
