// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Isaiah Cole's cattle drive, the script `isaiah`: the last hundred miles to
// Dodge City as the one row of `herd` in the world `drive`, with a row of
// `drive_log` for each beat and the trail name in `keepsake`. It models the
// herd's calm on night guard and the reading of it, the stampede and the head
// it scatters, the tracking, the river, the toll and the count at the gate,
// each by the guide's own rules and numbers.
//
// Args: `action`, one of `setup`, `sing` with `song`, `read` with `judge`,
// `settled` or `restless`, `stampede` with `flank`, `east` or `west`, `track`
// with `place`, `ridge`, `creek` or `draw`, `river` with `choice`, `wait` or
// `swim`, `toll` with `offer`, a whole number of head, `count`, `keepsake`,
// `exit` and `resume`. Returns `say`, the text the guide says, and `outcome`,
// as the log keeps it. A choice that fails is an outcome; a throw is a broken
// table, an unknown action or args of the wrong form.

// The store of the AI worker the script works through.
const store = engine.store;

// The world database that holds the drive.
const world = "drive";

// The head bound for Dodge City, from the introduction: two thousand head.
const HERD = 2000;

// The miles left to Dodge City, from the pitch: the last hundred miles.
const MILES = 100;

// The miles the herd walks in a day, by Isaiah's reckoning.
const MILES_A_DAY = 10;

// The head missing at sunrise, from the guide: forty head are missing.
const MISSING = 40;

// The herd's calm when it beds down, a game rule of 0 to 10.
const CALM_START = 5;

// The calm a song on night guard adds, a game rule.
const SONG_CALM = 3;

// The most calm a herd has, the top of the game rule's 0 to 10.
const CALM_MAX = 10;

// The least calm of a settled herd, a game rule.
const SETTLED_CALM = 7;

// The calm of a herd once its run is milled into a circle, a game rule.
const MILLED_CALM = 3;

// Where the missing head went, a game rule: bunches summing to `MISSING`.
const BUNCHES = Object.freeze({
  ridge: Object.freeze({
    head: 12,
    cover: "cedars",
    opening: "Up on the ridge",
  }),
  creek: Object.freeze({
    head: 25,
    cover: "willows",
    opening: "Along the creek",
  }),
  draw: Object.freeze({
    head: 3,
    cover: "plum thicket",
    opening: "Down in the draw",
  }),
});

// The looks before noon to find the scattered head, a game rule.
const LOOKS = 3;

// The head lost when a run reaches the breaks, a game rule.
const BREAKS_LOSS = 60;

// The head swum in high water for each one that drowns, a game rule.
const HIGH_WATER_PER = 100;

// The least toll in head the outfit at the ford takes, a game rule.
const TOLL_FLOOR = 20;

// A rider's wage in cents a day, a dollar a day by the guide's rule.
const WAGE_CENTS = 100;

// A whole number as the page shows it.
function whole_text(x) {
  return String(Math.round(x));
}

// Cents as dollars and cents, as `$11.00`.
function money_text(c) {
  return "$" + Math.floor(c / 100) + "." + String(c % 100).padStart(2, "0");
}

// A count of days with its word, as `1 day` or `11 days`.
function days_text(days) {
  return whole_text(days) + (days === 1 ? " day" : " days");
}

// The text an argument holds, which must not be empty.
function argument_text(args, name) {
  const value = args[name];
  if (typeof value !== "string" || value === "") {
    throw new Error(
      `Isaiah's script takes ${name} as text, not ${String(value)}.`,
    );
  }
  return value;
}

// The choice an argument holds, which must be one of those given.
function argument_choice(args, name, choices) {
  const value = args[name];
  if (!choices.includes(value)) {
    throw new Error(
      `Isaiah's script takes ${name} as one of ${choices.join(", ")},` +
        ` not ${String(value)}.`,
    );
  }
  return value;
}

// The whole number an argument holds, which must not be below 0.
function argument_whole(args, name) {
  const value = args[name];
  if (!Number.isInteger(value) || value < 0) {
    throw new Error(
      `Isaiah's script takes ${name} as a whole number, not ${String(value)}.`,
    );
  }
  return value;
}

// The one row of the herd, as an object of its columns.
function herd_read() {
  const [result] = store.sql_run(world, [
    {
      sql:
        "SELECT head, scattered, lost, tolled, calm, looks, found, waited," +
        " exits, song FROM herd WHERE id = 1",
      params: [],
    },
  ]);
  const [row] = result.rows;
  return Object.fromEntries(
    result.columns.map((name, index) => [name, row[index]]),
  );
}

// Writes the herd's counts and song back to its one row.
function herd_write(herd) {
  store.sql_run(world, [
    {
      sql:
        "UPDATE herd SET head = ?, scattered = ?, lost = ?, tolled = ?," +
        " calm = ?, looks = ?, found = ?, waited = ?, exits = ?, song = ?" +
        " WHERE id = 1",
      params: [
        herd.head,
        herd.scattered,
        herd.lost,
        herd.tolled,
        herd.calm,
        herd.looks,
        herd.found,
        herd.waited,
        herd.exits,
        herd.song,
      ],
    },
  ]);
}

// Logs the beat, the choice and the outcome, and returns what is said.
function beat_log(beat, choice, say, outcome) {
  store.sql_run(world, [
    {
      sql: "INSERT INTO drive_log (beat, choice, outcome) VALUES (?, ?, ?)",
      params: [beat, choice, outcome],
    },
  ]);
  return { say, outcome };
}

// Beds the herd down: its one row, at the start of the drive.
function herd_setup() {
  store.sql_run(world, [
    {
      sql:
        "INSERT INTO herd (id, head, scattered, lost, tolled, calm, looks," +
        " found, waited, exits, song) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
      params: [1, HERD, 0, 0, 0, CALM_START, 0, 0, 0, 0, ""],
    },
  ]);
  const say =
    `${whole_text(HERD)} head bedded on the flat and ${whole_text(MILES)}` +
    ` miles to Dodge City: ${days_text(MILES / MILES_A_DAY)} at` +
    ` ${whole_text(MILES_A_DAY)} miles a day. The herd's calm is` +
    ` ${whole_text(CALM_START)} of ${whole_text(CALM_MAX)}.`;
  return { say, outcome: "ready" };
}

// Sings on night guard, the song raising the herd's calm up to the most.
function herd_sing(args) {
  const song = argument_text(args, "song");
  const herd = herd_read();
  const before = herd.calm;
  herd.calm = Math.min(CALM_MAX, before + SONG_CALM);
  herd.song = song;
  herd_write(herd);
  const start = `You ride the slow circle singing ${song}, and the herd's calm`;
  const most = `of ${whole_text(CALM_MAX)}.`;
  if (herd.calm === before) {
    const say = `${start} holds at ${whole_text(before)} ${most}`;
    return beat_log("sing", song, say, "steady");
  }
  const say =
    `${start} comes up from ${whole_text(before)} to` +
    ` ${whole_text(herd.calm)} ${most}`;
  return beat_log("sing", song, say, "calmer");
}

// Rides the player back to the fire while Isaiah keeps the herd.
function fire_exit() {
  const herd = herd_read();
  herd.exits += 1;
  herd_write(herd);
  const say =
    "You ride back to the fire and the coffee. Isaiah keeps the circle" +
    ` alone, singing, and the ${whole_text(herd.head)} head stay down.`;
  return beat_log("exit", "fire", say, "at the fire");
}

// Rides the player out from the fire to the herd again.
function herd_resume() {
  const herd = herd_read();
  const say =
    `You ride out again to the herd: ${whole_text(herd.head)} head, calm` +
    ` ${whole_text(herd.calm)} of ${whole_text(CALM_MAX)}.`;
  return beat_log("resume", "herd", say, "riding");
}

// Reads the herd by its breathing, settled at `SETTLED_CALM` or more.
function herd_judge(args) {
  const judge = argument_choice(args, "judge", ["settled", "restless"]);
  const herd = herd_read();
  const settled = herd.calm >= SETTLED_CALM;
  const truth = settled ? "settled" : "restless";
  const sign = settled
    ? "Long slow breaths and the cud going"
    : "Short breaths and heads coming up";
  const calm = `calm ${whole_text(herd.calm)} of ${whole_text(CALM_MAX)}`;
  if (judge === truth) {
    const say = `${sign}: ${calm}, ${truth}, and you read it right.`;
    return beat_log("read", judge, say, "right");
  }
  const say = `${sign}: ${calm} is ${truth}, not ${judge}.`;
  return beat_log("read", judge, say, "wrong");
}

// Rides for a flank of the stampede: east bends it short of the breaks.
function stampede_turn(args) {
  const flank = argument_choice(args, "flank", ["east", "west"]);
  const herd = herd_read();
  herd.scattered = MISSING;
  herd.calm = MILLED_CALM;
  const looks = `and ${whole_text(LOOKS)} looks before noon to find them.`;
  if (flank === "east") {
    herd.head -= MISSING;
    herd_write(herd);
    const say =
      "You ride for the leaders on the east flank and bend the run west" +
      " into a circle, short of the breaks. At sunrise the count is" +
      ` ${whole_text(herd.head)}: ${whole_text(herd.scattered)} head` +
      ` scattered, ${looks}`;
    return beat_log("stampede", flank, say, "circled");
  }
  herd.head -= MISSING + BREAKS_LOSS;
  herd.lost += BREAKS_LOSS;
  herd_write(herd);
  const say =
    "You ride for the leaders on the west flank, and the run goes on east" +
    " into the breaks. At sunrise the count is" +
    ` ${whole_text(herd.head)}: ${whole_text(BREAKS_LOSS)} head lost in the` +
    ` breaks, ${whole_text(herd.scattered)} head scattered, ${looks}`;
  return beat_log("stampede", flank, say, "broken");
}

// Searches a place for its bunch, which a place searched before lacks.
function herd_track(args) {
  const place = argument_choice(args, "place", Object.keys(BUNCHES));
  const bunch = BUNCHES[place];
  const [searched] = store.sql_run(world, [
    {
      sql: "SELECT COUNT(*) FROM drive_log WHERE beat = ? AND choice = ?",
      params: ["track", place],
    },
  ]);
  const head = searched.rows[0][0] === 0 ? bunch.head : 0;
  const herd = herd_read();
  herd.head += head;
  herd.scattered -= head;
  herd.found += head;
  herd.looks += 1;
  const found =
    head > 0
      ? `${whole_text(head)} head in the ${bunch.cover}, driven back`
      : `nothing left in the ${bunch.cover}`;
  let say =
    `${bunch.opening}: ${found}. ${whole_text(herd.head)} with the herd,` +
    ` ${whole_text(herd.scattered)} still out, looks used` +
    ` ${whole_text(herd.looks)} of ${whole_text(LOOKS)}.`;
  const done = herd.scattered === 0 || herd.looks >= LOOKS;
  if (done && herd.scattered > 0) {
    say += ` The ${whole_text(herd.scattered)} still out are lost for good.`;
    herd.lost += herd.scattered;
    herd.scattered = 0;
  }
  herd_write(herd);
  return beat_log("track", place, say, done ? "done" : "searching");
}

// Crosses the Cimarron: waiting a day loses none, swimming it now drowns some.
function river_cross(args) {
  const choice = argument_choice(args, "choice", ["wait", "swim"]);
  const herd = herd_read();
  if (choice === "wait") {
    herd.waited += 1;
    herd_write(herd);
    const say =
      "You hold the herd a day on the south bank of the Cimarron and the" +
      ` water drops: all ${whole_text(herd.head)} swim it, leaders first,` +
      ` and none is lost. ${days_text(herd.waited)} spent waiting.`;
    return beat_log("river", choice, say, "crossed");
  }
  const swum = herd.head;
  const drowned = Math.floor(swum / HIGH_WATER_PER);
  herd.head -= drowned;
  herd.lost += drowned;
  herd_write(herd);
  const say =
    `You swim them now in high water: ${whole_text(swum)} go in,` +
    ` ${whole_text(drowned)} drown and ${whole_text(herd.head)} come out` +
    " on the north bank.";
  return beat_log("river", choice, say, "swum");
}

// Offers the outfit at the ford a toll in head, refused below `TOLL_FLOOR`.
function toll_pay(args) {
  const offer = argument_whole(args, "offer");
  if (offer < TOLL_FLOOR) {
    const say =
      `You offer ${whole_text(offer)} head. The outfit's boss spits:` +
      ` ${whole_text(TOLL_FLOOR)} is the least he takes.`;
    return beat_log("toll", String(offer), say, "refused");
  }
  const herd = herd_read();
  herd.head -= offer;
  herd.tolled += offer;
  herd_write(herd);
  const say =
    `You offer ${whole_text(offer)} head and the rope comes down:` +
    ` ${whole_text(herd.head)} head cross the ford.`;
  return beat_log("toll", String(offer), say, "paid");
}

// Counts the herd in at the stockyard gate and pays the days on the trail.
function herd_count() {
  const herd = herd_read();
  const days = MILES / MILES_A_DAY + herd.waited;
  const say =
    "At the stockyard gate the tally man counts" +
    ` ${whole_text(herd.head)} head: ${whole_text(HERD)} from the bed` +
    ` ground, ${whole_text(herd.tolled)} paid at the ford and` +
    ` ${whole_text(herd.lost)} lost on the trail. ${days_text(days)} on the` +
    ` trail at ${money_text(WAGE_CENTS)} a day:` +
    ` ${money_text(days * WAGE_CENTS)} in wages, and a bath.`;
  return beat_log("count", whole_text(herd.head), say, "delivered");
}

// Names the rider for the trail by the last word of the song sung.
function name_keep() {
  const herd = herd_read();
  const [stampede] = store.sql_run(world, [
    {
      sql:
        "SELECT outcome FROM drive_log WHERE beat = ? ORDER BY n DESC" +
        " LIMIT 1",
      params: ["stampede"],
    },
  ]);
  const deed = stampede.rows[0][0] === "circled" ? "turned" : "rode out";
  const name = herd.song.split(" ").at(-1);
  const text =
    `Trail name: ${name}. Rode night guard with Isaiah Cole, ${deed} the` +
    ` stampede, tracked ${whole_text(herd.found)} head and brought` +
    ` ${whole_text(herd.head)} to Dodge City.`;
  store.sql_run(world, [
    {
      sql: "INSERT INTO keepsake (kind, text) VALUES (?, ?)",
      params: ["trail name", text],
    },
  ]);
  return { say: text, outcome: "named" };
}

// Each action of the drive by the name the table passes as `action`.
const actions = Object.freeze({
  setup: herd_setup,
  sing: herd_sing,
  exit: fire_exit,
  resume: herd_resume,
  read: herd_judge,
  stampede: stampede_turn,
  track: herd_track,
  river: river_cross,
  toll: toll_pay,
  count: herd_count,
  keepsake: name_keep,
});

// An action the drive lacks is a broken table.
if (!Object.hasOwn(actions, args.action)) {
  throw new Error(`Isaiah's script has no action ${String(args.action)}.`);
}
return store.transaction_run(() => actions[args.action](args));
