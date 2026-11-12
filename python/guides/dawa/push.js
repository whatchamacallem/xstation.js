// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The step system `dawa_push`, kept at /_files/script/dawa_push.js: takes the
// intent `push`, its value `go`, at the camp below the first camp whose climb
// the guide times by a `leg`, the South Summit. The world's day is set to the
// hour of `departure`, and the rope starts its climb there, a tick at a time
// for the leg's minutes up. dawa_breathe draws its oxygen, dawa_move tells
// the arrival and dawa_stop the push stopped there, where a climber falls
// and the rope stops before the top, the outcome logged.
//
// Args: `ecs`. Reads `at`, `camp`, `leg`, `departure` and the clock; writes
// `day`, `climb` and `busy`. Says nothing itself, and logs the beat `push`
// with `go` and `stopped`.

// The step's view of the world, with its lib.
const ecs = args.ecs;
const lib = ecs.lib;

// Starts the rope up the timed leg above it, from the hour of the departure.
function push_go(intent) {
  if (intent.value !== "go") {
    throw new Error(
      `dawa_push: the value ${JSON.stringify(intent.value)} is not go.`,
    );
  }
  const here = lib.climber_camp(ecs, intent.entity);
  const next = lib.route_camp(ecs, here.ord + 1);
  const leg = lib.row_read(
    ecs,
    "SELECT up_minutes FROM leg WHERE entity = ?",
    [next.entity],
  );
  const departure = lib.row_read(ecs, "SELECT hour FROM departure", []);
  const ticks = leg.up_minutes / lib.tick_minutes(ecs);
  ecs.run([
    ...lib.day_set(departure.hour * lib.units.minutes_per_hour),
    ...lib.climb_start(here.entity, next.entity, ticks),
  ]);
  ecs.log("push", intent.value, "stopped");
}

const intent = ecs.take("push");
if (intent !== null) {
  push_go(intent);
}
