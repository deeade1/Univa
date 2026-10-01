/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/hooks/useCategories.js                    */
/* -------------------------------------------------------------------------- */

import { useCallback, useMemo, useState } from "react";
import { useQuery, useMutation } from "@apollo/client/react";

import {
  CATEGORIES_QUERY,
  CATEGORY_PRODUCTS_QUERY,
} from "@/modules/ecommerce/api/productQuery/queries/product";

import {
  CREATE_CATEGORY,
  UPDATE_CATEGORY,
  DELETE_CATEGORY,
} from "@/modules/ecommerce/api/productQuery/mutations/products";

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

const useCategories = ({
  first = 50,
  skip = false,
  parentId = null,
  onCompleted,
  onError,
} = {}) => {

  /* ------------------------------------------------------------------------ */
  /* State                                                                    */
  /* ------------------------------------------------------------------------ */

  const [selectedCategoryId, setSelectedCategoryId] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [expandedCategories, setExpandedCategories] = useState([]);

  /* ------------------------------------------------------------------------ */
  /* Categories Query                                                         */
  /* ------------------------------------------------------------------------ */

  const {
    data: categoriesData,
    loading: categoriesLoading,
    error: categoriesError,
    refetch: refetchCategories,
  } = useQuery(CATEGORIES_QUERY, {
    variables: { 
      first,
      parent: parentId,
    },
    skip,
    fetchPolicy: "cache-and-network",
    notifyOnNetworkStatusChange: true,
    onCompleted,
    onError,
  });

  /* ------------------------------------------------------------------------ */
  /* Category Products Query                                                  */
  /* ------------------------------------------------------------------------ */

  const {
    data: categoryProductsData,
    loading: categoryProductsLoading,
    error: categoryProductsError,
    refetch: refetchCategoryProducts,
  } = useQuery(CATEGORY_PRODUCTS_QUERY, {
    variables: {
      id: selectedCategoryId,
      first: 20,
    },
    skip: skip || !selectedCategoryId,
    fetchPolicy: "cache-and-network",
  });

  /* ------------------------------------------------------------------------ */
  /* Mutations                                                                */
  /* ------------------------------------------------------------------------ */

  const [
    createCategory,
    {
      loading: creatingCategory,
      error: createCategoryError,
    },
  ] = useMutation(CREATE_CATEGORY);

  const [
    updateCategory,
    {
      loading: updatingCategory,
      error: updateCategoryError,
    },
  ] = useMutation(UPDATE_CATEGORY);

  const [
    deleteCategory,
    {
      loading: deletingCategory,
      error: deleteCategoryError,
    },
  ] = useMutation(DELETE_CATEGORY);

  /* ------------------------------------------------------------------------ */
  /* Memoized Data                                                            */
  /* ------------------------------------------------------------------------ */

  const categories = useMemo(
    () => categoriesData?.allCategories?.edges?.map((edge) => edge.node) ?? [],
    [categoriesData]
  );

  const categoryProducts = useMemo(
    () => categoryProductsData?.category?.products?.edges?.map((edge) => edge.node) ?? [],
    [categoryProductsData]
  );

  /* ------------------------------------------------------------------------ */
  /* Category Hierarchy                                                       */
  /* ------------------------------------------------------------------------ */

  const categoryHierarchy = useMemo(() => {
    const buildTree = (items, parent = null) => {
      return items
        .filter(item => item.parent?.id === parent || (parent === null && !item.parent))
        .map(item => ({
          ...item,
          children: buildTree(items, item.id),
        }));
    };

    return buildTree(categories);
  }, [categories]);

  /* ------------------------------------------------------------------------ */
  /* Flat Category List (for dropdowns)                                       */
  /* ------------------------------------------------------------------------ */

  const flatCategories = useMemo(() => {
    const flatten = (items, depth = 0) => {
      let result = [];
      items.forEach(item => {
        result.push({ ...item, depth });
        if (item.children?.length) {
          result = [...result, ...flatten(item.children, depth + 1)];
        }
      });
      return result;
    };

    return flatten(categoryHierarchy);
  }, [categoryHierarchy]);

  /* ------------------------------------------------------------------------ */
  /* Filtered Categories                                                      */
  /* ------------------------------------------------------------------------ */

  const filteredCategories = useMemo(() => {
    if (!categoryFilter) return flatCategories;
    const search = categoryFilter.toLowerCase();
    return flatCategories.filter(
      (cat) =>
        cat.name.toLowerCase().includes(search) ||
        cat.slug.toLowerCase().includes(search)
    );
  }, [flatCategories, categoryFilter]);

  /* ------------------------------------------------------------------------ */
  /* Root Categories (no parent)                                             */
  /* ------------------------------------------------------------------------ */

  const rootCategories = useMemo(
    () => categoryHierarchy.filter((cat) => !cat.parent),
    [categoryHierarchy]
  );

  /* ------------------------------------------------------------------------ */
  /* Category Path / Breadcrumb                                               */
  /* ------------------------------------------------------------------------ */

  const getCategoryPath = useCallback(
    (categoryId) => {
      const path = [];
      let currentId = categoryId;

      while (currentId) {
        const category = categories.find((c) => c.id === currentId);
        if (!category) break;
        path.unshift(category);
        currentId = category.parent?.id;
      }

      return path;
    },
    [categories]
  );

  /* ------------------------------------------------------------------------ */
  /* Get Subcategories                                                        */
  /* ------------------------------------------------------------------------ */

  const getSubcategories = useCallback(
    (categoryId) => {
      return categories.filter((cat) => cat.parent?.id === categoryId);
    },
    [categories]
  );

  /* ------------------------------------------------------------------------ */
  /* Toggle Expanded Category                                                 */
  /* ------------------------------------------------------------------------ */

  const toggleExpanded = useCallback(
    (categoryId) => {
      setExpandedCategories((prev) =>
        prev.includes(categoryId)
          ? prev.filter((id) => id !== categoryId)
          : [...prev, categoryId]
      );
    },
    []
  );

  /* ------------------------------------------------------------------------ */
  /* Is Category Expanded                                                     */
  /* ------------------------------------------------------------------------ */

  const isExpanded = useCallback(
    (categoryId) => expandedCategories.includes(categoryId),
    [expandedCategories]
  );

  /* ------------------------------------------------------------------------ */
  /* Actions                                                                  */
  /* ------------------------------------------------------------------------ */

  /**
   * Create a new category
   */
  const createNewCategory = useCallback(
    async (input) => {
      try {
        const { data } = await createCategory({
          variables: { input },
        });

        const newCategory = data?.createCategory?.category;

        if (newCategory) {
          await refetchCategories();
          return {
            success: true,
            category: newCategory,
          };
        }

        return {
          success: false,
          message: "Failed to create category",
        };
      } catch (error) {
        return {
          success: false,
          error,
        };
      }
    },
    [createCategory, refetchCategories]
  );

  /**
   * Update an existing category
   */
  const updateExistingCategory = useCallback(
    async (id, input) => {
      try {
        const { data } = await updateCategory({
          variables: { input: { id, ...input } },
        });

        const updatedCategory = data?.updateCategory?.category;

        if (updatedCategory) {
          await refetchCategories();
          return {
            success: true,
            category: updatedCategory,
          };
        }

        return {
          success: false,
          message: "Failed to update category",
        };
      } catch (error) {
        return {
          success: false,
          error,
        };
      }
    },
    [updateCategory, refetchCategories]
  );

  /**
   * Delete a category
   */
  const deleteExistingCategory = useCallback(
    async (id) => {
      try {
        const { data } = await deleteCategory({
          variables: { input: { id } },
        });

        const success = data?.deleteCategory?.ok ?? false;

        if (success) {
          await refetchCategories();
          return {
            success: true,
          };
        }

        return {
          success: false,
          message: "Failed to delete category",
        };
      } catch (error) {
        return {
          success: false,
          error,
        };
      }
    },
    [deleteCategory, refetchCategories]
  );

  /**
   * Select a category and load its products
   */
  const selectCategory = useCallback(
    async (categoryId) => {
      setSelectedCategoryId(categoryId);
      if (categoryId) {
        await refetchCategoryProducts();
      }
      return categoryId;
    },
    [refetchCategoryProducts]
  );

  /**
   * Clear selected category
   */
  const clearSelectedCategory = useCallback(() => {
    setSelectedCategoryId(null);
  }, []);

  /**
   * Search categories by name or slug
   */
  const searchCategories = useCallback(
    (searchTerm) => {
      setCategoryFilter(searchTerm);
    },
    []
  );

  /**
   * Refresh all category data
   */
  const refresh = useCallback(async () => {
    await Promise.all([
      refetchCategories(),
      refetchCategoryProducts(),
    ]);
  }, [refetchCategories, refetchCategoryProducts]);

  /* ------------------------------------------------------------------------ */
  /* Error Normalization                                                      */
  /* ------------------------------------------------------------------------ */

  const error = useMemo(() => {
    const currentError =
      categoriesError ||
      categoryProductsError ||
      createCategoryError ||
      updateCategoryError ||
      deleteCategoryError;

    if (!currentError) return null;

    return {
      message: currentError.message ?? "Unable to load categories.",
      graphQLErrors: currentError.graphQLErrors ?? [],
      networkError: currentError.networkError ?? null,
    };
  }, [
    categoriesError,
    categoryProductsError,
    createCategoryError,
    updateCategoryError,
    deleteCategoryError,
  ]);

  /* ------------------------------------------------------------------------ */
  /* Loading States                                                           */
  /* ------------------------------------------------------------------------ */

  const loading =
    categoriesLoading ||
    categoryProductsLoading ||
    creatingCategory ||
    updatingCategory ||
    deletingCategory;

  /* ------------------------------------------------------------------------ */
  /* Return                                                                   */
  /* ------------------------------------------------------------------------ */

  return {
    // Data
    categories: flatCategories,
    categoryHierarchy,
    rootCategories,
    flatCategories,
    filteredCategories,
    categoryProducts,
    selectedCategoryId,
    expandedCategories,
    categoryFilter,

    // Loading
    loading,
    categoriesLoading,
    categoryProductsLoading,
    creatingCategory,
    updatingCategory,
    deletingCategory,

    // Error
    error,

    // Actions
    createNewCategory,
    updateExistingCategory,
    deleteExistingCategory,
    selectCategory,
    clearSelectedCategory,
    searchCategories,
    toggleExpanded,
    refresh,
    refetchCategories,
    refetchCategoryProducts,

    // Helpers
    getCategoryPath,
    getSubcategories,
    isExpanded,

    // Derived
    hasCategories: categories.length > 0,
    hasSubcategories: (categoryId) => getSubcategories(categoryId).length > 0,
    totalCategories: categories.length,
    totalProducts: categoryProducts.length,
  };
};

export default useCategories;