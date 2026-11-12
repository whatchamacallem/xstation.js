// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `isaiah_track` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_track.js`: takes the intent `track`, its value the
// name of the bunch searched, `ridge`, `creek` or `draw`, an entity of
// `cover`. A bunch still `hidden` is found: its `head` joins the herd's, the
// entity of `losses`, and counts in `losses.found`. A bunch found before
// holds nothing. Each search spends one of the rider's `looks`. With none
// still out or the looks spent, the tracking is done: the head still out are
// lost for good, and the herd, each entity of `pace`, sets out by `travel`
// for the next `place` ahead and is `busy`. It says what was found and what
// is left, and logs the beat `searching` or `done`.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `cover`, `hidden`,
// `head`, `looks`, `place` and `pace`. Writes `head`, `hidden`, `losses`,
// `looks.used`, `travel` and `busy`.

// The step's methods and the drive's lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The intent to search a place, taken, or none and no work this step.
const intent = ecs.take("track");
if (intent === null) {
  return;
}

// The bunch the value names, its cover and whether it is still hidden.
const bunch = lib.row_one(
  ecs.rows(
    "SELECT cover.entity AS entity, cover.name AS cover," +
      " cover.opening AS opening, EXISTS (SELECT 1 FROM hidden" +
      " WHERE hidden.entity = cover.entity) AS hidden FROM cover" +
      " JOIN entity ON entity.id = cover.entity WHERE entity.name = ?",
    [intent.value],
  ),
  `a bunch named ${JSON.stringify(intent.value)}`,
);
const herd = lib.row_one(
  ecs.rows("SELECT entity FROM losses ORDER BY entity", []),
  "the herd's losses",
);

// A hidden bunch is driven back whole, and each search spends a look.
const found =
  bunch.hidden === 1
    ? lib.row_one(
        ecs.rows("SELECT count FROM head WHERE entity = ?", [bunch.entity]),
        "the bunch's head",
      ).count
    : 0;
const statements = [
  {
    sql: "UPDATE looks SET used = used + 1 WHERE entity = ?",
    params: [intent.entity],
  },
];
if (bunch.hidden === 1) {
  statements.push(
    {
      sql: "UPDATE head SET count = count + ? WHERE entity = ?",
      params: [found, herd.entity],
    },
    {
      sql: "UPDATE losses SET found = found + ? WHERE entity = ?",
      params: [found, herd.entity],
    },
    { sql: "DELETE FROM head WHERE entity = ?", params: [bunch.entity] },
    { sql: "DELETE FROM hidden WHERE entity = ?", params: [bunch.entity] },
  );
}
ecs.run(statements);

const head = lib.row_one(
  ecs.rows("SELECT count FROM head WHERE entity = ?", [herd.entity]),
  "the herd's head",
).count;
const out = ecs.rows(
  "SELECT head.count AS count FROM head" +
    " JOIN hidden ON hidden.entity = head.entity ORDER BY head.entity",
  [],
);
const scattered = out.reduce((sum, left) => sum + left.count, 0);
const looks = lib.row_one(
  ecs.rows("SELECT used, most FROM looks WHERE entity = ?", [intent.entity]),
  "the rider's looks",
);

const told =
  found > 0
    ? `${lib.whole_text(found)} head in the ${bunch.cover}, driven back`
    : `nothing left in the ${bunch.cover}`;
let say =
  `${bunch.opening}: ${told}. ${lib.whole_text(head)} with the herd,` +
  ` ${lib.whole_text(scattered)} still out, looks used` +
  ` ${lib.whole_text(looks.used)} of ${lib.whole_text(looks.most)}.`;
const done = scattered === 0 || looks.used >= looks.most;
if (done) {
  const after = [];
  // The head still out when the looks are spent are lost for good.
  if (scattered > 0) {
    say += ` The ${lib.whole_text(scattered)} still out are lost for good.`;
    after.push(
      {
        sql: "UPDATE losses SET lost = lost + ? WHERE entity = ?",
        params: [scattered, herd.entity],
      },
      {
        sql: "DELETE FROM head WHERE entity IN (SELECT entity FROM hidden)",
        params: [],
      },
      { sql: "DELETE FROM hidden", params: [] },
    );
  }
  // The herd walks on to the next place ahead, the ticks moving it there.
  after.push(
    {
      sql:
        "INSERT INTO travel (entity, goal) SELECT place.entity," +
        " (SELECT ahead.entity FROM place AS ahead" +
        " WHERE ahead.mile > place.mile ORDER BY ahead.mile, ahead.entity" +
        " LIMIT 1) FROM place JOIN pace ON pace.entity = place.entity" +
        " ORDER BY place.entity",
      params: [],
    },
    {
      sql:
        "INSERT INTO busy (entity) SELECT travel.entity FROM travel" +
        " ORDER BY travel.entity",
      params: [],
    },
  );
  ecs.run(after);
}
ecs.say(say);
ecs.log("track", intent.value, done ? "done" : "searching");
