/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/utils/filters.js                          */
/* -------------------------------------------------------------------------- */

/**
 * ============================================================================
 * Ecommerce Filtering Utilities
 * ============================================================================
 *
 * Shared by:
 *
 * • Marketplace
 * • Search
 * • Categories
 * • Seller Store
 * • Wishlist
 * • Recommended Products
 * • Featured Products
 *
 * ============================================================================
 */

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const normalize = (value) =>
  String(value ?? "")
    .trim()
    .toLowerCase();

const number = (value) => {
  const n = Number(value);

  return Number.isFinite(n)
    ? n
    : 0;
};

/* -------------------------------------------------------------------------- */
/* Search                                                                     */
/* -------------------------------------------------------------------------- */

export function searchProducts(
  products = [],
  keyword = ""
) {
  if (!keyword?.trim()) {
    return [...products];
  }

  const query =
    normalize(keyword);

  return products.filter(
    (product) => {
      return (
        normalize(product.name).includes(
          query
        ) ||
        normalize(
          product.description
        ).includes(query) ||
        normalize(
          product.category
        ).includes(query) ||
        normalize(
          product.brand
        ).includes(query) ||
        normalize(
          product.seller
        ).includes(query) ||
        normalize(
          product.tags?.join(" ")
        ).includes(query)
      );
    }
  );
}

/* -------------------------------------------------------------------------- */
/* Category                                                                   */
/* -------------------------------------------------------------------------- */

export function filterByCategory(
  products = [],
  category = "all"
) {
  if (
    !category ||
    category === "all"
  ) {
    return [...products];
  }

  return products.filter(
    (product) =>
      normalize(
        product.category
      ) ===
      normalize(category)
  );
}

/* -------------------------------------------------------------------------- */
/* Brand                                                                      */
/* -------------------------------------------------------------------------- */

export function filterByBrand(
  products = [],
  brand = "all"
) {
  if (
    !brand ||
    brand === "all"
  ) {
    return [...products];
  }

  return products.filter(
    (product) =>
      normalize(product.brand) ===
      normalize(brand)
  );
}

/* -------------------------------------------------------------------------- */
/* Seller                                                                     */
/* -------------------------------------------------------------------------- */

export function filterBySeller(
  products = [],
  seller = "all"
) {
  if (
    !seller ||
    seller === "all"
  ) {
    return [...products];
  }

  return products.filter(
    (product) =>
      normalize(product.seller) ===
      normalize(seller)
  );
}

/* -------------------------------------------------------------------------- */
/* Price                                                                      */
/* -------------------------------------------------------------------------- */

export function filterByPrice(
  products = [],
  {
    min = 0,
    max = Infinity,
  } = {}
) {
  return products.filter(
    (product) => {
      const price = number(
        product.price_per_unit
      );

      return (
        price >= min &&
        price <= max
      );
    }
  );
}

/* -------------------------------------------------------------------------- */
/* Rating                                                                     */
/* -------------------------------------------------------------------------- */

export function filterByRating(
  products = [],
  minimum = 0
) {
  return products.filter(
    (product) =>
      number(product.rating) >=
      minimum
  );
}

/* -------------------------------------------------------------------------- */
/* Availability                                                               */
/* -------------------------------------------------------------------------- */

export function filterInStock(
  products = [],
  onlyInStock = false
) {
  if (!onlyInStock) {
    return [...products];
  }

  return products.filter(
    (product) =>
      number(product.stock) > 0
  );
}

/* -------------------------------------------------------------------------- */
/* Discount                                                                   */
/* -------------------------------------------------------------------------- */

export function filterDiscounted(
  products = []
) {
  return products.filter(
    (product) =>
      number(
        product.originalPrice
      ) >
      number(
        product.price_per_unit
      )
  );
}

/* -------------------------------------------------------------------------- */
/* Featured                                                                   */
/* -------------------------------------------------------------------------- */

export function filterFeatured(
  products = []
) {
  return products.filter(
    (product) => product.featured
  );
}

/* -------------------------------------------------------------------------- */
/* Recommended                                                                */
/* -------------------------------------------------------------------------- */

export function filterRecommended(
  products = []
) {
  return products.filter(
    (product) =>
      product.recommended
  );
}

/* -------------------------------------------------------------------------- */
/* Sorting                                                                    */
/* -------------------------------------------------------------------------- */

export function sortProducts(
  products = [],
  sort = "popular"
) {
  const list = [...products];

  switch (sort) {
    case "price-low":
      return list.sort(
        (a, b) =>
          number(
            a.price_per_unit
          ) -
          number(
            b.price_per_unit
          )
      );

    case "price-high":
      return list.sort(
        (a, b) =>
          number(
            b.price_per_unit
          ) -
          number(
            a.price_per_unit
          )
      );

    case "rating":
      return list.sort(
        (a, b) =>
          number(b.rating) -
          number(a.rating)
      );

    case "reviews":
      return list.sort(
        (a, b) =>
          number(
            b.reviewCount
          ) -
          number(
            a.reviewCount
          )
      );

    case "stock":
      return list.sort(
        (a, b) =>
          number(b.stock) -
          number(a.stock)
      );

    case "alphabetical":
      return list.sort((a, b) =>
        a.name.localeCompare(
          b.name
        )
      );

    case "newest":
      return list.sort(
        (a, b) =>
          new Date(
            b.createdAt
          ) -
          new Date(
            a.createdAt
          )
      );

    default:
      return list;
  }
}

/* -------------------------------------------------------------------------- */
/* Suggestions                                                                */
/* -------------------------------------------------------------------------- */

export function searchSuggestions(
  products = [],
  keyword = "",
  limit = 8
) {
  if (!keyword?.trim()) {
    return [];
  }

  return searchProducts(
    products,
    keyword
  ).slice(0, limit);
}

/* -------------------------------------------------------------------------- */
/* Categories                                                                 */
/* -------------------------------------------------------------------------- */

export function uniqueCategories(
  products = []
) {
  return [
    "all",
    ...new Set(
      products
        .map(
          (item) =>
            item.category
        )
        .filter(Boolean)
    ),
  ];
}

/* -------------------------------------------------------------------------- */
/* Brands                                                                     */
/* -------------------------------------------------------------------------- */

export function uniqueBrands(
  products = []
) {
  return [
    "all",
    ...new Set(
      products
        .map(
          (item) =>
            item.brand
        )
        .filter(Boolean)
    ),
  ];
}

/* -------------------------------------------------------------------------- */
/* Sellers                                                                    */
/* -------------------------------------------------------------------------- */

export function uniqueSellers(
  products = []
) {
  return [
    "all",
    ...new Set(
      products
        .map(
          (item) =>
            item.seller
        )
        .filter(Boolean)
    ),
  ];
}

/* -------------------------------------------------------------------------- */
/* Pipeline                                                                    */
/* -------------------------------------------------------------------------- */

export function filterProducts(
  products = [],
  options = {}
) {
  let result = [...products];

  result = searchProducts(
    result,
    options.search
  );

  result =
    filterByCategory(
      result,
      options.category
    );

  result =
    filterByBrand(
      result,
      options.brand
    );

  result =
    filterBySeller(
      result,
      options.seller
    );

  result =
    filterByPrice(
      result,
      {
        min:
          options.minPrice,
        max:
          options.maxPrice,
      }
    );

  result =
    filterByRating(
      result,
      options.rating
    );

  result =
    filterInStock(
      result,
      options.inStock
    );

  result = sortProducts(
    result,
    options.sort
  );

  return result;
}

/* -------------------------------------------------------------------------- */
/* Default Export                                                             */
/* -------------------------------------------------------------------------- */

export default {
  searchProducts,

  filterByCategory,

  filterByBrand,

  filterBySeller,

  filterByPrice,

  filterByRating,

  filterInStock,

  filterDiscounted,

  filterFeatured,

  filterRecommended,

  sortProducts,

  searchSuggestions,

  uniqueCategories,

  uniqueBrands,

  uniqueSellers,

  filterProducts,
};