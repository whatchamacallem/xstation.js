// SPDX-FileCopyrightText: © 2026 Adrian Johnston.
// SPDX-License-Identifier: MIT
// This file is licensed under the terms of the LICENSE.md file.
//
// Tests of the order and accounting of the images the media cache keeps, on
// real decoded images: each `ImageBitmap` is taken from an `OffscreenCanvas`
// of the size the test chose, which gives it at once, and a closed image is
// one that reports no size, as the platform makes it.

namespace test_media_cache {
  // The values the tests share.
  const constants = Object.freeze({
    // The cache budget in bytes, a size its writer chose.
    budget: 1000,
    pixel_bytes: 4,
    context_kind: "2d" as const,
  });

  // A real image of the size in pixels, taken from a canvas of that size.
  function image_sized(width: number, height: number): ImageBitmap {
    const canvas = new OffscreenCanvas(width, height);
    canvas.getContext(constants.context_kind);
    return canvas.transferToImageBitmap();
  }

  // An image one pixel high that counts as the given number of bytes.
  function image_make(bytes: number): ImageBitmap {
    return image_sized(bytes / constants.pixel_bytes, 1);
  }

  // Whether the image was closed, which leaves it with no size.
  function closed_is(image: ImageBitmap): boolean {
    return image.width === 0 && image.height === 0;
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
      cache.image_put("a", image_sized(10, 10));
      cache.image_put("b", image_sized(5, 10));
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
      this.assertEqual([first, second].map(closed_is), [false, false]);
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
      this.assertEqual(images.map(closed_is), [true, false, false]);
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
      this.assertEqual(images.map(closed_is), [true, false, false, false]);
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
      this.assertEqual(images.map(closed_is), [true, true, true, false]);
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
      this.assertEqual([older, larger].map(closed_is), [true, false]);
    }

    // An image over the budget is kept in an empty cache.
    test_oversize_first(): void {
      const cache = cache_make();
      const larger = image_make(1600);
      cache.image_put("a", larger);
      this.assertEqual(cache.keys_list(), ["a"]);
      this.assertEqual(cache.total_bytes(), 1600);
      this.assertFalse(closed_is(larger));
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
      this.assertEqual([larger, next].map(closed_is), [true, false]);
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
      this.assertEqual([old, other, fresh].map(closed_is), [
        true,
        false,
        false,
      ]);
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
      this.assertEqual([old, other, fresh].map(closed_is), [
        true,
        true,
        false,
      ]);
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

Object.freeze(test_media_cache);
