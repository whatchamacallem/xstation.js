// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The database administration the engine seeds, the AI's to edit. It makes
// a universe database with a `world` table, a world database with a
// `region` table and a region database, records the universe in `metaverse`
// and makes the new world the current one.
//
// Args: `title` and `region`, and optionally `universe`, default
// `current_universe`, and `world`, default `world`. Every name is a C
// identifier. Optional `player` switches the player in use. Optional
// `scene`, an object of `id`, `subtitle` and optionally `image`, is written
// in the region database and entered. Returns `universe`, `world`, `region`
// and, when a scene was entered, its Document-Ref as `scene`.

// The store of the AI worker the script works through.
const store = engine.store;

// Encodes the text the script writes, because KV values are bytes.
const text = new TextEncoder();

// The names, with the defaults `current_universe` and `world`.
const universe = args.universe ?? "current_universe";
const world = args.world ?? "world";
const { title, region } = args;

// The player the universe row names: the one given or the one in use.
const player =
  args.player ??
  new TextDecoder().decode(store.kv_get("/metaverse/player").data);

// Creates the universe database with its `world` table and the world row.
store.db_create(universe);
store.sql_run(universe, [
  {
    sql:
      "CREATE TABLE world (name TEXT PRIMARY KEY, title TEXT NOT NULL) " +
      "STRICT",
    params: [],
  },
  { sql: "INSERT INTO world VALUES (?, ?)", params: [world, title] },
]);

// Creates the world database with its `region` table and the region row.
store.db_create(world);
store.sql_run(world, [
  {
    sql:
      "CREATE TABLE region (name TEXT PRIMARY KEY, " +
      "tide INTEGER NOT NULL DEFAULT 0) STRICT",
    params: [],
  },
  { sql: "INSERT INTO region (name) VALUES (?)", params: [region] },
]);

// Creates the region database.
store.db_create(region);

// Records the universe in `metaverse` for the player and the world.
store.sql_run("metaverse", [
  {
    sql: "INSERT INTO universe VALUES (?, ?, ?, ?)",
    params: [universe, title, player, world],
  },
]);

// The result: the names made, and the scene when one is entered.
const result = { universe, world, region };

// Writes the scene in the region database and points the world at it.
if (args.scene !== undefined) {
  const { id, subtitle, image } = args.scene;
  const body = { 0: { t: "scene" }, subtitle };
  if (image !== undefined) {
    body[1] = image;
    body.image = { $ref: 1 };
  }
  const put = store.doc_put(region, id, body);
  store.kv_put("/" + world + "/scene", text.encode(put.ref));
  result.scene = put.ref;
}

// Switches the player in use when one is given.
if (args.player !== undefined) {
  store.kv_put("/metaverse/player", text.encode(args.player));
}

// Makes the new world the current one.
store.kv_put("/metaverse/world", text.encode(world));

return result;
