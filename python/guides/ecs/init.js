// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The core script `ecs_init`, kept at /_files/script/ecs_init.js: makes the
// tables of the entity-component-system core in a guide's world database, in
// one sql_run and so one push. `entity` holds the entities, `system` the
// schedule of the scripts a step runs, `clock` the time of the entity
// `world`, `intent` the player's choices waiting for a step system, `busy`
// the entities a tick system still moves, `output` every fragment a step said
// and `beat_log` the one beat each step logs. Every table is STRICT, and each
// component is keyed by its entity, deleted with it.
//
// Args: `world`, the world database, which must exist. Returns `world`.

// The store of the AI worker the script works through.
const store = engine.store;

// The world database, which the args must name.
if (typeof args.world !== "string" || args.world === "") {
  throw new Error(
    `ecs_init takes world as the name of a database, not` +
      ` ${JSON.stringify(args.world)}.`,
  );
}
const world = args.world;

// The DDL of the core tables, in the order they are made.
const TABLES = Object.freeze([
  "CREATE TABLE entity (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)" +
    " STRICT",
  "CREATE TABLE system (ord INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE," +
    " kind TEXT NOT NULL CHECK (kind IN ('lib', 'step', 'tick'))) STRICT",
  "CREATE TABLE clock (entity INTEGER PRIMARY KEY REFERENCES entity (id)" +
    " ON DELETE CASCADE, step INTEGER NOT NULL, tick INTEGER NOT NULL," +
    " tick_seconds INTEGER NOT NULL, ticks_max INTEGER NOT NULL) STRICT",
  "CREATE TABLE intent (entity INTEGER PRIMARY KEY REFERENCES entity (id)" +
    " ON DELETE CASCADE, verb TEXT NOT NULL, value TEXT NOT NULL) STRICT",
  "CREATE TABLE busy (entity INTEGER PRIMARY KEY REFERENCES entity (id)" +
    " ON DELETE CASCADE) STRICT",
  "CREATE TABLE output (n INTEGER PRIMARY KEY, step INTEGER NOT NULL," +
    " tick INTEGER NOT NULL, system TEXT NOT NULL, text TEXT NOT NULL)" +
    " STRICT",
  "CREATE TABLE beat_log (n INTEGER PRIMARY KEY, step INTEGER NOT NULL," +
    " tick INTEGER NOT NULL, beat TEXT NOT NULL, choice TEXT NOT NULL," +
    " outcome TEXT NOT NULL) STRICT",
]);

store.sql_run(world, TABLES.map((sql) => ({ sql, params: [] })));
return { world };
