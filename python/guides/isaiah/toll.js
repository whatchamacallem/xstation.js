// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `isaiah_toll` of Isaiah Cole's cattle drive, kept at
// `/_files/script/isaiah_toll.js`: takes the intent `toll`, its value the
// head offered in digits, as `20`, to the outfit at the ford, the entity of
// `toll`. An offer below its `toll.floor` is refused and changes nothing.
// One at the floor or more is paid: the herd, the entity of `losses`, gives
// the head, counted in `losses.tolled`, and each entity of `pace` sets out by
// `travel` for the next `place` ahead and is `busy`. It says the offer and
// what came of it, and logs the beat `refused` or `paid`.
//
// Args: `ecs`, of the contract of `ecs_step`. Reads `toll`, `losses`,
// `head`, `place` and `pace`. Writes `head`, `losses.tolled`, `travel` and
// `busy`.

// The step's methods and the drive's lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The intent to pay the toll, taken, or none and no work this step.
const intent = ecs.take("toll");
if (intent === null) {
  return;
}
const offer = lib.whole_read(intent.value);

const outfit = lib.row_one(
  ecs.rows("SELECT floor FROM toll ORDER BY entity", []),
  "the outfit's toll",
);
// The boss takes no offer below his floor.
if (offer < outfit.floor) {
  ecs.say(
    `You offer ${lib.whole_text(offer)} head. The outfit's boss spits:` +
      ` ${lib.whole_text(outfit.floor)} is the least he takes.`,
  );
  ecs.log("toll", intent.value, "refused");
  return;
}

const herd = lib.row_one(
  ecs.rows("SELECT entity FROM losses ORDER BY entity", []),
  "the herd's losses",
);
ecs.run([
  {
    sql: "UPDATE head SET count = count - ? WHERE entity = ?",
    params: [offer, herd.entity],
  },
  {
    sql: "UPDATE losses SET tolled = tolled + ? WHERE entity = ?",
    params: [offer, herd.entity],
  },
  // The herd walks on to the next place ahead, the ticks moving it there.
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
]);
const after = lib.row_one(
  ecs.rows("SELECT count FROM head WHERE entity = ?", [herd.entity]),
  "the herd's head",
);
ecs.say(
  `You offer ${lib.whole_text(offer)} head and the rope comes down:` +
    ` ${lib.whole_text(after.count)} head cross the ford.`,
);
ecs.log("toll", intent.value, "paid");
