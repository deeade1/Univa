/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/VariantSelector.jsx    */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useMemo,
    useCallback,
} from "react";

import {
    StyleSheet,
    Text,
    TouchableOpacity,
    View,
} from "react-native";

import PropTypes
    from "prop-types";

import theme
    from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import Divider
    from "../common/Divider";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const VariantSelector = memo(({

    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    variants = [],

    selectedVariants = {},

    /* ---------------------------------------------------------------------- */
    /* Behavior                                                               */
    /* ---------------------------------------------------------------------- */

    disabled = false,

    showDivider = true,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onSelectionChange,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style,

}) => {

    const {
        colors,
        spacing,
    } = theme;

    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    const variantGroups =
        useMemo(

            () => variants,

            [variants]

        );

    /* ---------------------------------------------------------------------- */
    /* Selection Handler                                                      */
    /* ---------------------------------------------------------------------- */

    const handleSelect =
        useCallback(

            (

                variantId,

                option,

            ) => {

                if (disabled) {

                    return;

                }

                onSelectionChange?.(

                    variantId,

                    option

                );

            },

            [

                disabled,

                onSelectionChange,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Helper - Get Selected Value                                            */
    /* ---------------------------------------------------------------------- */

    const getSelectedValue =
        useCallback(

            (variantId) => {

                const selected =
                    selectedVariants?.[variantId];

                // Handle both string/primitive and object selections
                if (typeof selected === "object") {
                    return selected?.value;
                }

                return selected;

            },

            [selectedVariants]

        );

    /* ---------------------------------------------------------------------- */
    /* Helper - Get Display Label                                             */
    /* ---------------------------------------------------------------------- */

    const getDisplayLabel =
        useCallback(

            (option) => {

                const value = option?.value;

                // If option has a separate label, use it
                if (option?.label) {
                    return option.label;
                }

                // Otherwise use value
                return value;

            },

            []

        );

    /* ---------------------------------------------------------------------- */
    /* Component                                                              */
    /* ---------------------------------------------------------------------- */

    return (

        <View
            style={[

                styles.container,

                style,

            ]}
        >

            {variantGroups.map(

                (group) => {

                    const {

                        id,

                        name,

                        type = "text",

                        options = [],

                    } = group;

                    const selectedValue =
                        getSelectedValue(id);

                    return (

                        <View

                            key={id}

                            style={
                                styles.group
                            }

                        >

                            {/* -------------------------------------------------- */}
                            {/* Group Title                                       */}
                            {/* -------------------------------------------------- */}

                            <Text
                                style={[

                                    styles.groupTitle,

                                    {

                                        color:
                                            colors.text,

                                    },

                                ]}
                            >

                                {name}

                            </Text>

                            {/* -------------------------------------------------- */}
                            {/* Options                                           */}
                            {/* -------------------------------------------------- */}

                            <View
                                style={
                                    styles.optionsContainer
                                }
                            >

                                {options.map(

                                    (

                                        option,

                                        index,

                                    ) => {

                                        const value =
                                            option?.value;

                                        const color =
                                            option?.color;

                                        const isDisabled =
                                            option?.disabled ??
                                            false;

                                        const isSelected =
                                            selectedValue ===
                                            value;

                                        const displayLabel =
                                            getDisplayLabel(option);

                                        return (

                                            <TouchableOpacity

                                                key={
                                                    option?.id ??
                                                    `${id}-${index}`
                                                }

                                                activeOpacity={
                                                    0.7
                                                }

                                                disabled={
                                                    disabled ||
                                                    isDisabled
                                                }

                                                onPress={() =>

                                                    handleSelect(

                                                        id,

                                                        option

                                                    )

                                                }

                                                accessibilityRole="button"

                                                accessibilityState={{

                                                    selected: isSelected,
                                                    disabled: disabled || isDisabled,

                                                }}

                                                accessibilityLabel={
                                                    `${name}: ${displayLabel}`
                                                }

                                                style={[

                                                    styles.option,

                                                    isSelected && {

                                                        borderColor:
                                                            colors.primary,

                                                        backgroundColor:
                                                            colors.primaryContainer ??
                                                            colors.surfaceVariant,

                                                    },

                                                    (disabled ||
                                                        isDisabled) &&

                                                    styles.disabledOption,

                                                ]}

                                            >

                                                {/* ---------- Color Variant ---------- */}

                                                {type === "color" ? (

                                                    <View
                                                        style={styles.colorOptionContent}
                                                    >

                                                        <View

                                                            style={[

                                                                styles.colorSwatch,

                                                                {

                                                                    backgroundColor:
                                                                        color,

                                                                },

                                                                isSelected && {

                                                                    borderColor:
                                                                        colors.primary,

                                                                    borderWidth:
                                                                        2,

                                                                },

                                                            ]}

                                                        />

                                                        <Text
                                                            style={[

                                                                styles.colorLabel,

                                                                {

                                                                    color:
                                                                        isSelected
                                                                            ? colors.primary
                                                                            : colors.text,

                                                                },

                                                            ]}
                                                        >

                                                            {displayLabel}

                                                        </Text>

                                                    </View>

                                                ) : (

                                                    <Text

                                                        style={[

                                                            styles.optionText,

                                                            {

                                                                color:
                                                                    isSelected
                                                                        ? colors.primary
                                                                        : colors.text,

                                                            },

                                                        ]}

                                                    >

                                                        {displayLabel}

                                                    </Text>

                                                )}

                                            </TouchableOpacity>

                                        );

                                    }

                                )}

                            </View>

                            {showDivider && (

                                <Divider
                                    spacing={16}
                                />

                            )}

                        </View>

                    );

                }

            )}

            {/* ------------------------------------------------------------------ */}
            {/* Selection Summary                                                 */}
            {/* ------------------------------------------------------------------ */}

            {!!variantGroups.length && (

                <View
                    style={
                        styles.summaryContainer
                    }
                >

                    {variantGroups.map(

                        (group) => {

                            const selected =
                                selectedVariants?.[
                                    group.id
                                ];

                            if (!selected) {

                                return null;

                            }

                            const displayValue =
                                typeof selected === "object"
                                    ? selected?.value
                                    : selected;

                            return (

                                <View

                                    key={
                                        `${group.id}-summary`
                                    }

                                    style={
                                        styles.summaryItem
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

                                        {group.name}:

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

                                        {displayValue}

                                    </Text>

                                </View>

                            );

                        }

                    )}

                </View>

            )}

        </View>

    );

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

VariantSelector.displayName =
    "VariantSelector";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

VariantSelector.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    variants:
        PropTypes.arrayOf(

            PropTypes.shape({

                id:
                    PropTypes.string
                        .isRequired,

                name:
                    PropTypes.string
                        .isRequired,

                type:
                    PropTypes.oneOf([

                        "text",

                        "color",

                    ]),

                options:
                    PropTypes.arrayOf(

                        PropTypes.shape({

                            id:
                                PropTypes.oneOfType([

                                    PropTypes.string,

                                    PropTypes.number,

                                ]),

                            value:
                                PropTypes.oneOfType([

                                    PropTypes.string,

                                    PropTypes.number,

                                ]).isRequired,

                            label:
                                PropTypes.string,

                            color:
                                PropTypes.string,

                            disabled:
                                PropTypes.bool,

                        })

                    ),

            })

        ),

    selectedVariants:
        PropTypes.object,

    /* ---------------------------------------------------------------------- */
    /* Behaviour                                                              */
    /* ---------------------------------------------------------------------- */

    disabled:
        PropTypes.bool,

    showDivider:
        PropTypes.bool,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onSelectionChange:
        PropTypes.func,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style:
        PropTypes.oneOfType([

            PropTypes.object,

            PropTypes.array,

        ]),

};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
    StyleSheet.create({

        /* ------------------------------------------------------------------ */
        /* Container                                                          */
        /* ------------------------------------------------------------------ */

        container: {

            paddingHorizontal:
                theme.spacing.md,

            paddingVertical:
                theme.spacing.sm,

        },

        /* ------------------------------------------------------------------ */
        /* Variant Group                                                      */
        /* ------------------------------------------------------------------ */

        group: {

            marginBottom:
                theme.spacing.sm,

        },

        groupTitle: {

            fontSize:
                16,

            fontWeight:
                "700",

            marginBottom:
                theme.spacing.md,

        },

        /* ------------------------------------------------------------------ */
        /* Options                                                            */
        /* ------------------------------------------------------------------ */

        optionsContainer: {

            flexDirection:
                "row",

            flexWrap:
                "wrap",

            marginHorizontal:
                -4,

            marginBottom:
                theme.spacing.sm,

        },

        option: {

            minWidth:
                48,

            minHeight:
                40,

            paddingHorizontal:
                theme.spacing.md,

            paddingVertical:
                theme.spacing.sm,

            margin:
                4,

            borderRadius:
                12,

            borderWidth:
                1,

            borderColor:
                theme.colors.outline ??
                "#D1D5DB",

            justifyContent:
                "center",

            alignItems:
                "center",

        },

        disabledOption: {

            opacity:
                0.45,

        },

        optionText: {

            fontSize:
                14,

            fontWeight:
                "600",

        },

        /* ------------------------------------------------------------------ */
        /* Color Variant                                                      */
        /* ------------------------------------------------------------------ */

        colorOptionContent: {

            flexDirection:
                "row",

            alignItems:
                "center",

        },

        colorSwatch: {

            width:
                24,

            height:
                24,

            borderRadius:
                12,

            borderWidth:
                1,

            borderColor:
                theme.colors.outlineVariant ??
                "#E5E7EB",

            marginRight:
                8,

        },

        colorLabel: {

            fontSize:
                14,

            fontWeight:
                "500",

        },

        /* ------------------------------------------------------------------ */
        /* Selection Summary                                                  */
        /* ------------------------------------------------------------------ */

        summaryContainer: {

            marginTop:
                theme.spacing.md,

        },

        summaryItem: {

            flexDirection:
                "row",

            alignItems:
                "center",

            marginBottom:
                theme.spacing.xs,

        },

        summaryLabel: {

            fontSize:
                14,

            fontWeight:
                "600",

            marginRight:
                theme.spacing.xs,

        },

        summaryValue: {

            fontSize:
                14,

            fontWeight:
                "500",

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    VariantSelector;