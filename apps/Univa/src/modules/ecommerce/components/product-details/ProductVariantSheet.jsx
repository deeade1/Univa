/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductVariantSheet.jsx                                                    */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useState,
  useMemo,
  useCallback,
  useEffect,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
} from "react-native";

import BottomSheet, {
  BottomSheetScrollView,
} from "@gorhom/bottom-sheet";

import { MaterialCommunityIcons } from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Variant Option                                                             */
/* -------------------------------------------------------------------------- */

const VariantOption = memo(
  ({
    option,
    selected,
    colors,
    onPress,
  }) => (
    <Pressable
      onPress={() =>
        onPress(option)
      }
      style={[
        styles.option,
        {
          borderColor: selected
            ? colors.primary
            : colors.border,

          backgroundColor:
            selected
              ? colors.primary +
                "12"
              : colors.card,
        },
      ]}
    >
      {!!option.color && (
        <View
          style={[
            styles.colorPreview,
            {
              backgroundColor:
                option.color,
            },
          ]}
        />
      )}

      <Text
        style={[
          styles.optionText,
          {
            color: selected
              ? colors.primary
              : colors.text,
          },
        ]}
      >
        {option.label}
      </Text>

      {selected && (
        <MaterialCommunityIcons
          name="check-circle"
          size={18}
          color={
            colors.primary
          }
        />
      )}
    </Pressable>
  )
);

VariantOption.displayName =
  "VariantOption";

/* -------------------------------------------------------------------------- */
/* Variant Group                                                              */
/* -------------------------------------------------------------------------- */

const VariantGroup = memo(
  ({
    variant,
    selectedValue,
    colors,
    onSelect,
  }) => (
    <View
      style={styles.group}
    >
      <Text
        style={[
          styles.groupTitle,
          {
            color:
              colors.text,
          },
        ]}
      >
        {variant.name}
      </Text>

      <View
        style={
          styles.optionsContainer
        }
      >
        {variant.options.map(
          (option) => (
            <VariantOption
              key={
                option.id ??
                option.value
              }
              option={option}
              selected={
                selectedValue ===
                option.value
              }
              colors={colors}
              onPress={() =>
                onSelect(
                  variant.key,
                  option.value
                )
              }
            />
          )
        )}
      </View>
    </View>
  )
);

VariantGroup.displayName =
  "VariantGroup";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductVariantSheet =
  memo(
    ({
      sheetRef,

      product,

      visible,

      variants = [],

      initialSelection =
        {},

      snapPoints = [
        "70%",
      ],

      onApply,

      onClose,

      style,
    }) => {
      const { colors } =
        theme;

      const variantData =
        useMemo(() => {
          if (
            variants.length >
            0
          ) {
            return variants;
          }

          return (
            product?.variants ??
            []
          );
        }, [
          variants,
          product,
        ]);

      const [
        selectedVariants,
        setSelectedVariants,
      ] = useState(
        initialSelection
      );

      useEffect(() => {
        setSelectedVariants(
          initialSelection
        );
      }, [
        initialSelection,
      ]);

      const handleSelect =
        useCallback(
          (
            key,
            value
          ) => {
            setSelectedVariants(
              (
                previous
              ) => ({
                ...previous,
                [key]:
                  value,
              })
            );
          },
          []
        );

      const handleApply =
        useCallback(() => {
          onApply?.(
            selectedVariants
          );

          onClose?.();
        }, [
          selectedVariants,
          onApply,
          onClose,
        ]);

      return (
        <BottomSheet
          ref={sheetRef}
          index={
            visible
              ? 0
              : -1
          }
          snapPoints={
            snapPoints
          }
          enablePanDownToClose
          onClose={
            onClose
          }
          backgroundStyle={{
            backgroundColor:
              colors.card,
          }}
          handleIndicatorStyle={{
            backgroundColor:
              colors.border,
          }}
        >
          <BottomSheetScrollView
            style={[
              styles.container,
              style,
            ]}
          >
            {/* ---------------------------------------------------------- */}
            {/* Header                                                     */}
            {/* ---------------------------------------------------------- */}

            <View
              style={
                styles.header
              }
            >
              <View>
                <Text
                  style={[
                    styles.title,
                    {
                      color:
                        colors.text,
                    },
                  ]}
                >
                  Select Options
                </Text>

                <Text
                  style={[
                    styles.subtitle,
                    {
                      color:
                        colors.textSecondary,
                    },
                  ]}
                >
                  Choose your preferred
                  product variants
                </Text>
              </View>

              <Pressable
                onPress={
                  onClose
                }
              >
                <MaterialCommunityIcons
                  name="close"
                  size={24}
                  color={
                    colors.text
                  }
                />
              </Pressable>
            </View>
                        {/* ---------------------------------------------------------- */}
            {/* Selected Variants Summary                                  */}
            {/* ---------------------------------------------------------- */}

            {Object.keys(
              selectedVariants
            ).length > 0 && (
              <View
                style={[
                  styles.summaryContainer,
                  {
                    borderColor:
                      colors.border,
                    backgroundColor:
                      colors.background,
                  },
                ]}
              >
                <Text
                  style={[
                    styles.summaryTitle,
                    {
                      color:
                        colors.text,
                    },
                  ]}
                >
                  Selected Options
                </Text>

                {variantData.map(
                  (variant) => {
                    const value =
                      selectedVariants[
                        variant.key
                      ];

                    if (!value) {
                      return null;
                    }

                    const option =
                      variant.options.find(
                        (item) =>
                          item.value ===
                          value
                      );

                    return (
                      <View
                        key={
                          variant.key
                        }
                        style={
                          styles.summaryRow
                        }
                      >
                        <Text
                          style={[
                            styles.summaryLabel,
                            {
                              color:
                                colors.textSecondary,
                            },
                          ]}
                        >
                          {variant.name}
                        </Text>

                        <Text
                          style={[
                            styles.summaryValue,
                            {
                              color:
                                colors.text,
                            },
                          ]}
                        >
                          {option?.label ??
                            value}
                        </Text>
                      </View>
                    );
                  }
                )}

                <View
                  style={
                    styles.summaryRow
                  }
                >
                  <Text
                    style={[
                      styles.summaryLabel,
                      {
                        color:
                          colors.textSecondary,
                      },
                    ]}
                  >
                    Quantity
                  </Text>

                  <Text
                    style={[
                      styles.summaryValue,
                      {
                        color:
                          colors.text,
                      },
                    ]}
                  >
                    {selectedVariants.quantity ??
                      1}
                  </Text>
                </View>
              </View>
            )}

            {/* ---------------------------------------------------------- */}
            {/* Bottom Actions                                             */}
            {/* ---------------------------------------------------------- */}

            <View
              style={[
                styles.footer,
                {
                  borderTopColor:
                    colors.border,
                },
              ]}
            >
              <Pressable
                onPress={() =>
                  setSelectedVariants(
                    initialSelection
                  )
                }
                style={[
                  styles.resetButton,
                  {
                    borderColor:
                      colors.border,
                  },
                ]}
              >
                <MaterialCommunityIcons
                  name="refresh"
                  size={18}
                  color={
                    colors.text
                  }
                />

                <Text
                  style={[
                    styles.resetText,
                    {
                      color:
                        colors.text,
                    },
                  ]}
                >
                  Reset
                </Text>
              </Pressable>

              <Pressable
                onPress={
                  handleApply
                }
                style={[
                  styles.applyButton,
                  {
                    backgroundColor:
                      colors.primary,
                  },
                ]}
              >
                <MaterialCommunityIcons
                  name="check-circle-outline"
                  size={20}
                  color="#FFFFFF"
                />

                <Text
                  style={
                    styles.applyText
                  }
                >
                  Apply Selection
                </Text>
              </Pressable>
            </View>
          </BottomSheetScrollView>
        </BottomSheet>
      );
    }
);

ProductVariantSheet.displayName =
  "ProductVariantSheet";
  /* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const optionShape = PropTypes.shape({
  id: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.number,
  ]),

  label:
    PropTypes.string
      .isRequired,

  value:
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]).isRequired,

  color:
    PropTypes.string,
});

const variantShape =
  PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    key:
      PropTypes.string
        .isRequired,

    name:
      PropTypes.string
        .isRequired,

    options:
      PropTypes.arrayOf(
        optionShape
      ).isRequired,
  });

const productShape =
  PropTypes.shape({
    name:
      PropTypes.string,

    price:
      PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
      ]),

    inStock:
      PropTypes.bool,

    stockLabel:
      PropTypes.string,

    variants:
      PropTypes.arrayOf(
        variantShape
      ),
  });

VariantOption.propTypes = {
  option:
    optionShape
      .isRequired,

  selected:
    PropTypes.bool,

  colors:
    PropTypes.object
      .isRequired,

  onPress:
    PropTypes.func
      .isRequired,
};

VariantOption.defaultProps = {
  selected: false,
};

VariantGroup.propTypes = {
  variant:
    variantShape
      .isRequired,

  selectedValue:
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

  colors:
    PropTypes.object
      .isRequired,

  onSelect:
    PropTypes.func
      .isRequired,
};

VariantGroup.defaultProps = {
  selectedValue: null,
};

ProductVariantSheet.propTypes =
  {
    sheetRef:
      PropTypes.oneOfType([
        PropTypes.func,
        PropTypes.shape({
          current:
            PropTypes.any,
        }),
      ]),

    visible:
      PropTypes.bool,

    product:
      productShape,

    variants:
      PropTypes.arrayOf(
        variantShape
      ),

    initialSelection:
      PropTypes.object,

    snapPoints:
      PropTypes.arrayOf(
        PropTypes.oneOfType([
          PropTypes.string,
          PropTypes.number,
        ])
      ),

    onApply:
      PropTypes.func,

    onClose:
      PropTypes.func,

    style:
      PropTypes.oneOfType([
        PropTypes.object,
        PropTypes.array,
      ]),
  };

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

ProductVariantSheet.defaultProps =
  {
    sheetRef: null,

    visible: false,

    product: null,

    variants: [],

    initialSelection:
      {},

    snapPoints: [
      "70%",
    ],

    onApply: null,

    onClose: null,

    style: null,
  };

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    container: {
      flex: 1,

      paddingHorizontal: 20,

      paddingBottom: 40,
    },

    /* ------------------------------------------------------------------ */
    /* Header                                                             */
    /* ------------------------------------------------------------------ */

    header: {
      flexDirection: "row",

      justifyContent:
        "space-between",

      alignItems:
        "flex-start",

      marginBottom: 20,
    },

    title: {
      fontSize: 20,

      fontWeight: "700",
    },

    subtitle: {
      marginTop: 4,

      fontSize: 14,
    },

    /* ------------------------------------------------------------------ */
    /* Product                                                            */
    /* ------------------------------------------------------------------ */

    productCard: {
      borderWidth: 1,

      borderRadius: 16,

      padding: 16,

      marginBottom: 24,
    },

    productName: {
      fontSize: 17,

      fontWeight: "700",
    },

    productMeta: {
      flexDirection: "row",

      justifyContent:
        "space-between",

      alignItems: "center",

      marginTop: 10,
    },

    productPrice: {
      fontSize: 20,

      fontWeight: "700",
    },

    stockContainer: {
      flexDirection: "row",

      alignItems: "center",
    },

    stockText: {
      marginLeft: 6,

      fontSize: 13,

      fontWeight: "600",
    },

    /* ------------------------------------------------------------------ */
    /* Groups                                                             */
    /* ------------------------------------------------------------------ */

    group: {
      marginBottom: 24,
    },

    groupTitle: {
      fontSize: 16,

      fontWeight: "700",

      marginBottom: 12,
    },

    optionsContainer: {
      flexDirection: "row",

      flexWrap: "wrap",
    },

    option: {
      flexDirection: "row",

      alignItems: "center",

      borderWidth: 1,

      borderRadius: 12,

      paddingHorizontal: 14,

      paddingVertical: 10,

      marginRight: 10,

      marginBottom: 10,
    },

    colorPreview: {
      width: 18,

      height: 18,

      borderRadius: 9,

      marginRight: 8,
    },

    optionText: {
      fontSize: 14,

      fontWeight: "600",

      marginRight: 8,
    },

    /* ------------------------------------------------------------------ */
    /* Quantity                                                           */
    /* ------------------------------------------------------------------ */

    quantitySection: {
      marginBottom: 24,
    },

    quantityContainer: {
      flexDirection: "row",

      alignItems: "center",
    },

    quantityButton: {
      width: 42,

      height: 42,

      borderWidth: 1,

      borderRadius: 10,

      justifyContent: "center",

      alignItems: "center",
    },

    quantityValue: {
      minWidth: 48,

      textAlign: "center",

      fontSize: 18,

      fontWeight: "700",
    },

    /* ------------------------------------------------------------------ */
    /* Summary                                                            */
    /* ------------------------------------------------------------------ */

    summaryContainer: {
      borderWidth: 1,

      borderRadius: 16,

      padding: 16,

      marginBottom: 24,
    },

    summaryTitle: {
      fontSize: 16,

      fontWeight: "700",

      marginBottom: 12,
    },

    summaryRow: {
      flexDirection: "row",

      justifyContent:
        "space-between",

      marginBottom: 8,
    },

    summaryLabel: {
      fontSize: 14,
    },

    summaryValue: {
      fontSize: 14,

      fontWeight: "600",
    },

    /* ------------------------------------------------------------------ */
    /* Footer                                                             */
    /* ------------------------------------------------------------------ */

    footer: {
      flexDirection: "row",

      borderTopWidth: 1,

      paddingTop: 20,

      marginTop: 8,
    },

    resetButton: {
      flex: 1,

      flexDirection: "row",

      justifyContent: "center",

      alignItems: "center",

      borderWidth: 1,

      borderRadius: 14,

      paddingVertical: 14,

      marginRight: 10,
    },

    resetText: {
      marginLeft: 8,

      fontSize: 15,

      fontWeight: "600",
    },

    applyButton: {
      flex: 2,

      flexDirection: "row",

      justifyContent: "center",

      alignItems: "center",

      borderRadius: 14,

      paddingVertical: 14,
    },

    applyText: {
      marginLeft: 8,

      color: "#FFFFFF",

      fontSize: 15,

      fontWeight: "700",
    },
  });

export default ProductVariantSheet;