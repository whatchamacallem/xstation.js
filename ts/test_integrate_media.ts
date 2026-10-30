// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// The block of the media port's line cases on the page: `media.store` and
// `media.fetch` lines answered with real decodes and real fetches. For now it
// holds the tests of the order and accounting of the images the cache keeps,
// moved from `test_media` as they were, whose `ImageDouble` stands for a
// decoded image until these tests run on real ones.

namespace test_integrate_media {
  // The values the tests share.
  const constants = Object.freeze({
    // The cache budget in bytes, a size its writer chose.
    budget: 1000,
    pixel_bytes: 4,
  });

  // An image that counts its closes and, once closed, reports no size.
  class ImageDouble {
    width: number;
    height: number;
    closes = 0;

    // Takes the size of the image in pixels.
    constructor(width: number, height: number) {
      this.width = width;
      this.height = height;
    }

    // Counts the close and drops the size.
    close(): void {
      this.closes += 1;
      this.width = 0;
      this.height = 0;
    }
  }

  // An image one pixel high that counts as the given number of bytes.
  function image_make(bytes: number): ImageDouble {
    return new ImageDouble(bytes / constants.pixel_bytes, 1);
  }

  // A cache with the budget of the tests.
  function cache_make(): media.ImageCache {
    return new media.ImageCache(constants.budget);
  }

  // The order and accounting of the images a cache keeps.
  export class TestCacheEviction extends unittest.TestCase {
    // Each image counts as its width times height times 4 bytes.
    test_bytes_counted(): void {
      const cache = cache_make();
      cache.image_put("a", new ImageDouble(10, 10));
      cache.image_put("b", new ImageDouble(5, 10));
      this.assertEqual(cache.total_bytes(), 600);
      this.assertEqual(cache.keys_list(), ["a", "b"]);
    }

    // A total exactly at the budget is within it, so nothing is evicted.
    test_budget_exact(): void {
      const cache = cache_make();
      const first = image_make(400);
      const second = image_make(600);
      cache.image_put("a", first);
      cache.image_put("b", second);
      this.assertEqual(cache.total_bytes(), constants.budget);
      this.assertEqual(cache.keys_list(), ["a", "b"]);
      this.assertEqual(first.closes + second.closes, 0);
    }

    // The oldest goes first, closed, and the total drops by its counted bytes.
    test_oldest_evicted(): void {
      const cache = cache_make();
      const images = [image_make(400), image_make(400), image_make(400)];
      cache.image_put("a", images[0]);
      cache.image_put("b", images[1]);
      cache.image_put("c", images[2]);
      this.assertEqual(cache.keys_list(), ["b", "c"]);
      this.assertEqual(cache.total_bytes(), 800);
      this.assertEqual(cache.image_get("a"), undefined);
      this.assertTrue(cache.image_get("b") === images[1]);
      this.assertTrue(cache.image_get("c") === images[2]);
      this.assertEqual(
        images.map((image) => image.closes),
        [1, 0, 0],
      );
    }

    // Eviction stops as soon as the total fits, so the younger images stay.
    test_evict_least(): void {
      const cache = cache_make();
      const images = [
        image_make(400),
        image_make(200),
        image_make(200),
        image_make(600),
      ];
      images.forEach((image, index) => {
        cache.image_put("abcd"[index], image);
      });
      this.assertEqual(cache.keys_list(), ["b", "c", "d"]);
      this.assertEqual(cache.total_bytes(), 1000);
      this.assertEqual(
        images.map((image) => image.closes),
        [1, 0, 0, 0],
      );
    }

    // One large image evicts every older image, oldest first.
    test_evict_many(): void {
      const cache = cache_make();
      const images = [
        image_make(400),
        image_make(200),
        image_make(200),
        image_make(1000),
      ];
      images.forEach((image, index) => {
        cache.image_put("abcd"[index], image);
      });
      this.assertEqual(cache.keys_list(), ["d"]);
      this.assertEqual(cache.total_bytes(), 1000);
      this.assertEqual(
        images.map((image) => image.closes),
        [1, 1, 1, 0],
      );
    }

    // The newest image is kept alone though it is over the budget.
    test_newest_alone(): void {
      const cache = cache_make();
      const older = image_make(400);
      const larger = image_make(1600);
      cache.image_put("a", older);
      cache.image_put("b", larger);
      this.assertEqual(cache.keys_list(), ["b"]);
      this.assertEqual(cache.total_bytes(), 1600);
      this.assertTrue(cache.image_get("b") === larger);
      this.assertEqual([older.closes, larger.closes], [1, 0]);
    }

    // An image over the budget is kept in an empty cache.
    test_oversize_first(): void {
      const cache = cache_make();
      const larger = image_make(1600);
      cache.image_put("a", larger);
      this.assertEqual(cache.keys_list(), ["a"]);
      this.assertEqual(cache.total_bytes(), 1600);
      this.assertEqual(larger.closes, 0);
    }

    // The next image evicts an oversize one, as the oldest image goes first.
    test_oversize_evicted(): void {
      const cache = cache_make();
      const larger = image_make(1600);
      const next = image_make(400);
      cache.image_put("a", larger);
      cache.image_put("b", next);
      this.assertEqual(cache.keys_list(), ["b"]);
      this.assertEqual(cache.total_bytes(), 400);
      this.assertEqual([larger.closes, next.closes], [1, 0]);
    }

    // A key kept again closes the old image and makes the new one newest.
    test_key_replaced(): void {
      const cache = cache_make();
      const old = image_make(400);
      const other = image_make(200);
      const fresh = image_make(600);
      cache.image_put("a", old);
      cache.image_put("b", other);
      cache.image_put("a", fresh);
      this.assertEqual(cache.keys_list(), ["b", "a"]);
      this.assertEqual(cache.total_bytes(), 800);
      this.assertTrue(cache.image_get("a") === fresh);
      this.assertEqual([old.closes, other.closes, fresh.closes], [1, 0, 0]);
    }

    // A replacement can evict, and the old image is not counted twice.
    test_replace_evicts(): void {
      const cache = cache_make();
      const old = image_make(400);
      const other = image_make(400);
      const fresh = image_make(800);
      cache.image_put("a", old);
      cache.image_put("b", other);
      cache.image_put("a", fresh);
      this.assertEqual(cache.keys_list(), ["a"]);
      this.assertEqual(cache.total_bytes(), 800);
      this.assertEqual([old.closes, other.closes, fresh.closes], [1, 1, 0]);
    }

    // Looking an image up does not make it newer.
    test_lookup_order(): void {
      const cache = cache_make();
      cache.image_put("a", image_make(400));
      cache.image_put("b", image_make(400));
      this.assertFalse(cache.image_get("a") === undefined);
      cache.image_put("c", image_make(400));
      this.assertEqual(cache.keys_list(), ["b", "c"]);
    }

    // A key that was never kept has no image.
    test_get_missing(): void {
      const cache = cache_make();
      this.assertEqual(cache.image_get("a"), undefined);
      cache.image_put("b", image_make(400));
      this.assertEqual(cache.image_get("a"), undefined);
    }
  }
}

Object.freeze(test_integrate_media);
