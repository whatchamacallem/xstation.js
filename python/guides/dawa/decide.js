// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `dawa_decide`, kept at /_files/script/dawa_decide.js: takes
// the intent `decide`, its value `rescue` or `summit`, the player's call at
// the camp below the top while a climber is down. On `rescue` the climber
// who is down breathes the guide's spare at a sick climber's flow, and the
// rope starts down to the camp below, a tick at a time for the leg's minutes
// down; dawa_breathe draws the oxygen and dawa_rescue tells it. On `summit`,
// a branch no walk takes, the top, the way back and Teo's descent with the
// other rope are worked out at once with no tick, the bottles moving whole:
// the player breathes his own bottle dry, then the spare, which stays on the
// rope, for the rest of the way down; the climber who is down goes with the
// other rope on his empty bottle and is carried in alive. The rope ends at
// the camp below, the high mark the top and Dawa's record broken.
//
// Args: `ecs`. Reads `at`, `camp`, `leg`, `breathe`, `bottle`, `limits`,
// `down`, `oxygen`, `day` and the clock; writes `breathe`, `climb` and
// `busy`, and on `summit` `high`, `record`, `bottle`, `down`, `at` and `day`.
// Logs the beat `decide` with the call and `rescued` or `summited`.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// The values of the intent, the player's call.
const RESCUE = "rescue";
const SUMMIT = "summit";

// The minutes of the legs from the camp below the top: up to the top, back from it, and down to the camp below.
function legs_read(here, top) {
  return lib.row_read(
    ecs,
    "SELECT here.down_minutes AS down, top.up_minutes AS up," +
      " top.down_minutes AS back FROM leg AS here, leg AS top" +
      " WHERE here.entity = ? AND top.entity = ?",
    [here.entity, top.entity],
  );
}

// Takes the climber who is down to the camp below on the guide's spare, a tick at a time.
function rescue_start(state) {
  const teo = state.legs.down * state.oxygen.sick_lpm;
  const used = state.legs.down * state.you.lpm;
  if (teo > state.spare.left_l || used > state.you.left_l) {
    throw new Error(
      "dawa_decide: the rescue runs out of oxygen, so there is no choice.",
    );
  }
  const ticks = state.legs.down / lib.tick_minutes(ecs);
  ecs.run([
    {
      sql: "INSERT INTO breathe (entity, lpm, bottle) VALUES (?, ?, ?)",
      params: [state.fallen.entity, state.oxygen.sick_lpm, state.spare.entity],
    },
    ...lib.climb_start(state.here.entity, state.below.entity, ticks),
  ]);
}

// Goes to the top and back to the camp below on your bottle then the spare, the bottles whole, worked out at once, the record broken.
function summit_take(state) {
  const units = lib.units;
  const { legs, you, spare } = state;
  const round = legs.up + legs.back + legs.down;
  const lasts = you.left_l / you.lpm;
  const borrowed = round * you.lpm - you.left_l;
  const empty = lib.row_read(
    ecs,
    "SELECT left_l FROM bottle WHERE holder = ?",
    [state.fallen.entity],
  );
  if (
    !Number.isInteger(lasts) ||
    borrowed <= 0 ||
    borrowed > spare.left_l ||
    empty.left_l !== 0
  ) {
    throw new Error(
      `dawa_decide: the top takes ${borrowed} litres of the spare's` +
        ` ${spare.left_l} after ${lasts} minutes on your bottle, and the` +
        ` bottle of the climber who is down holds ${empty.left_l}, which is` +
        " no stake.",
    );
  }
  const day = lib.row_read(ecs, "SELECT minute FROM day", []);
  const per_day = units.hours_per_day * units.minutes_per_hour;
  ecs.run([
    {
      sql: "UPDATE high SET m = MAX(m, ?) WHERE entity = ?",
      params: [state.top.altitude_m, state.player],
    },
    { sql: "UPDATE record SET text = ?", params: ["broken"] },
    {
      sql: "UPDATE bottle SET left_l = left_l - ? WHERE entity = ?",
      params: [you.left_l, you.bottle],
    },
    {
      sql: "UPDATE bottle SET left_l = left_l - ? WHERE entity = ?",
      params: [borrowed, spare.entity],
    },
    {
      sql: "UPDATE breathe SET bottle = ? WHERE entity = ?",
      params: [spare.entity, state.player],
    },
    {
      sql: "DELETE FROM down WHERE entity = ?",
      params: [state.fallen.entity],
    },
    ...lib.rope_move(state.here.entity, state.below.entity),
    {
      sql: "UPDATE day SET minute = ?",
      params: [(day.minute + round) % per_day],
    },
  ]);
  ecs.say(
    `You and Dawa go on, and at ${lib.clock_text(day.minute + legs.up)} you ` +
      `stand on the top, ${state.top.altitude_m} m. Your bottle runs dry at ` +
      `${lib.clock_text(day.minute + lasts)}, and Dawa's spare gives you the ` +
      `last ${borrowed} litres, ${lib.duration_text(round - lasts)} at ` +
      `${you.lpm} litres a minute, down to ${state.below.name} at ` +
      `${lib.clock_text(day.minute + round)}. Teo goes down with the other ` +
      `rope on his empty bottle, ${lib.duration_text(legs.down)} with no ` +
      `oxygen, and they carry him in to ${state.below.name} alive. Dawa's ` +
      "record is broken.",
  );
}

// Follows the player's call: the climber who is down taken down on the spare, or the top and the record broken.
function decide_call(intent) {
  const choice = intent.value;
  if (choice !== RESCUE && choice !== SUMMIT) {
    throw new Error(
      `dawa_decide: the value ${JSON.stringify(choice)} is neither` +
        ` ${RESCUE} nor ${SUMMIT}.`,
    );
  }
  const player = intent.entity;
  const ends = lib.route_ends(ecs);
  const here = lib.climber_camp(ecs, player);
  if (here.ord !== ends.top - 1) {
    throw new Error(
      `dawa_decide: the rope is at ${here.name}, not at the camp below the` +
        " top.",
    );
  }
  const top = lib.route_camp(ecs, ends.top);
  const state = {
    player,
    here,
    top,
    below: lib.route_camp(ecs, here.ord - 1),
    legs: legs_read(here, top),
    oxygen: lib.oxygen_read(ecs),
    fallen: lib.row_read(ecs, "SELECT entity FROM down", []),
    you: lib.row_read(
      ecs,
      "SELECT breathe.lpm AS lpm, bottle.entity AS bottle," +
        " bottle.left_l AS left_l FROM breathe JOIN bottle" +
        " ON bottle.entity = breathe.bottle WHERE breathe.entity = ?",
      [player],
    ),
    spare: lib.row_read(
      ecs,
      "SELECT bottle.entity AS entity, bottle.left_l AS left_l FROM bottle" +
        " JOIN limits ON limits.entity = bottle.holder",
      [],
    ),
  };
  if (choice === RESCUE) {
    rescue_start(state);
    ecs.log("decide", choice, "rescued");
  } else {
    summit_take(state);
    ecs.log("decide", choice, "summited");
  }
}

const intent = ecs.take("decide");
if (intent !== null) {
  decide_call(intent);
}
