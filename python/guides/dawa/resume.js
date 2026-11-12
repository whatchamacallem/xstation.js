// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `dawa_resume`, kept at /_files/script/dawa_resume.js: takes
// the intent `resume`, the player's words to climb again after an exit. The
// rope climbs back at once to the camp the exit left, the player's `resume`,
// with the air there, or goes on from where it is when the exit left the
// bottom, and the exit is no longer held. A climber who is down at the camp
// it leaves is carried back up with the rope, and the say names him. A resume
// with no exit held is a bug of the table, and throws.
//
// Args: `ecs`. Reads `resume`, `at`, `camp` and `down`; writes `resume`, `at` and
// `high`. Says the way back, and logs the beat `resume` with the player's
// words and `up`.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// Brings the rope back up to the camp the exit left.
function resume_up(intent) {
  const player = intent.entity;
  const held = ecs.rows(
    "SELECT camp.ord AS ord FROM resume JOIN camp" +
      " ON camp.entity = resume.camp WHERE resume.entity = ?",
    [player],
  );
  if (held.length !== 1) {
    throw new Error("dawa_resume: there is no exit to resume from.");
  }
  const back = lib.route_camp(ecs, held[0].ord);
  const here = lib.climber_camp(ecs, player);
  const rise = back.altitude_m - here.altitude_m;
  const air = lib.air_text(back.place, back.altitude_m);
  const statements = [
    { sql: "DELETE FROM resume WHERE entity = ?", params: [player] },
  ];
  let say = `We go on from ${air}`;
  if (back.entity !== here.entity) {
    const fallen = lib.fallen_names(ecs, here.entity);
    const carrying =
      fallen.length === 0 ? "" : `, carrying ${fallen.join(" and ")} with the rope,`;
    statements.push(...lib.rope_move(here.entity, back.entity));
    say = `Back up ${rise} m${carrying} to ${air}`;
  }
  ecs.run(statements);
  ecs.say(say);
  ecs.log("resume", intent.value, "up");
}

const intent = ecs.take("resume");
if (intent !== null) {
  resume_up(intent);
}
