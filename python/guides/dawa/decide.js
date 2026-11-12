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
// other rope are worked out at once with no tick: the rope ends at the camp
// below, both bottles spent, the high mark the top and Dawa's record broken.
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

// Goes to the top on the spare and back to the camp below, worked out at once, the record broken.
function summit_take(state) {
  const units = lib.units;
  const { legs, you, spare, oxygen } = state;
  const round = legs.up + legs.back + legs.down;
  const needed = round * you.lpm;
  const borrowed = needed - you.left_l;
  const left = spare.left_l - borrowed;
  const lasts = left / oxygen.sick_lpm;
  const shortfall = legs.down - lasts;
  if (borrowed < 0 || !Number.isInteger(lasts) || shortfall <= 0) {
    throw new Error(
      `dawa_decide: the top takes ${borrowed} litres of the spare and leaves` +
        ` Teo ${lasts} minutes of the ${legs.down} he needs, which is no stake.`,
    );
  }
  const day = lib.row_read(ecs, "SELECT minute FROM day", []);
  const topped = day.minute + legs.up;
  const per_day = units.hours_per_day * units.minutes_per_hour;
  const down = lib.duration_text(legs.down);
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
      params: [borrowed + left, spare.entity],
    },
    { sql: "DELETE FROM down", params: [] },
    ...lib.rope_move(state.here.entity, state.below.entity),
    {
      sql: "UPDATE day SET minute = ?",
      params: [(day.minute + round) % per_day],
    },
  ]);
  ecs.say(
    `You and Dawa go on, and at ${lib.clock_text(topped)} you stand on the ` +
      `top, ${state.top.altitude_m} m, on ${borrowed} litres of his spare. ` +
      `Teo goes down with the other rope on the ${left} left, ` +
      `${lib.duration_text(lasts)} at ${oxygen.sick_lpm} litres a minute of ` +
      `the ${down} he needs: his oxygen runs out ${shortfall} minutes above the ` +
      "Col, and they carry him in alive. Dawa's record is broken.",
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
