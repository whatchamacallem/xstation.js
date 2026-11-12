// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `dawa_exit`, kept at /_files/script/dawa_exit.js: takes the
// intent `exit`, the player's words to go down, the exit that always works.
// It keeps the camp the player left as `resume` and counts the exit; Dawa
// clips the player to the fixed line and the rope goes down at once to the
// camp below, its time stated by no band, with the air there, or at the
// bottom of the route stays, as it is the bottom already. An exit taken
// while one is held is a bug of the table, and throws.
//
// Args: `ecs`. Reads `resume`, `at` and `camp`; writes `resume`, `exits`,
// `at` and `high`. Says the way down, and logs the beat `exit` with the
// player's words and `down`.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// Takes the rope down to the camp below, keeping the camp it left.
function exit_down(intent) {
  const player = intent.entity;
  const held = ecs.rows("SELECT camp FROM resume WHERE entity = ?", [player]);
  if (held.length > 0) {
    throw new Error(
      "dawa_exit: the climber is down already, waiting to resume.",
    );
  }
  const here = lib.climber_camp(ecs, player);
  const statements = [
    {
      sql: "INSERT INTO resume (entity, camp) VALUES (?, ?)",
      params: [player, here.entity],
    },
    {
      sql: "UPDATE exits SET count = count + 1 WHERE entity = ?",
      params: [player],
    },
  ];
  let say;
  if (here.ord === lib.route_ends(ecs).bottom) {
    say = "We are at the bottom already.";
  } else {
    const below = lib.route_camp(ecs, here.ord - 1);
    const drop = here.altitude_m - below.altitude_m;
    statements.push(...lib.rope_move(here.entity, below.entity));
    say =
      `Dawa clips you to the fixed line and takes you down ${drop} m to ` +
      lib.air_text(below.place, below.altitude_m);
  }
  ecs.run(statements);
  ecs.say(say);
  ecs.log("exit", intent.value, "down");
}

const intent = ecs.take("exit");
if (intent !== null) {
  exit_down(intent);
}
