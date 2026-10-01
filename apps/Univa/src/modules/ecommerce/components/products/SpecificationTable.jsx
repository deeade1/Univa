/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/SpecificationTable.jsx */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useState,
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

import LoadingOverlay
    from "../common/LoadingOverlay";

import EmptyState
    from "../common/EmptyState";

import ErrorState
    from "../common/ErrorState";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const SpecificationTable = memo(({

    /* ---------------------------------------------------------------------- */
    /* Content                                                                */
    /* ---------------------------------------------------------------------- */

    title = "Specifications",

    specifications = [],

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    expandable = true,

    collapsedRows = 6,

    readMoreLabel = "Show More",

    readLessLabel = "Show Less",

    zebraRows = true,

    grouped = false,

    /* ---------------------------------------------------------------------- */
    /* State                                                                  */
    /* ---------------------------------------------------------------------- */

    loading = false,

    error = null,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onRetry,

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
    /* Local State                                                            */
    /* ---------------------------------------------------------------------- */

    const [

        expanded,

        setExpanded,

    ] = useState(false);

    /* ---------------------------------------------------------------------- */
    /* Data                                                                   */
    /* ---------------------------------------------------------------------- */

    const data =
        useMemo(

            () =>

                Array.isArray(
                    specifications
                )

                    ? specifications

                    : [],

            [

                specifications,

            ]

        );

    const hasSpecifications =
        useMemo(

            () =>

                data.length > 0,

            [

                data,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Visible Rows                                                           */
    /* ---------------------------------------------------------------------- */

    const visibleSpecifications =
        useMemo(

            () => {

                if (

                    !expandable ||

                    expanded ||

                    grouped

                ) {

                    return data;

                }

                return data.slice(

                    0,

                    collapsedRows

                );

            },

            [

                data,

                expandable,

                expanded,

                grouped,

                collapsedRows,

            ]

        );

    const showToggle =
        useMemo(

            () =>

                expandable &&

                !grouped &&

                data.length >

                collapsedRows,

            [

                expandable,

                grouped,

                data,

                collapsedRows,

            ]

        );

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleToggle =
        useCallback(

            () => {

                setExpanded(

                    previous =>

                        !previous

                );

            },

            []

        );

    /* ---------------------------------------------------------------------- */
    /* Loading State                                                          */
    /* ---------------------------------------------------------------------- */

    if (loading) {

        return (

            <View
                style={[

                    styles.container,

                    style,

                ]}
            >

                <LoadingOverlay

                    visible

                    fullscreen={false}

                    transparent

                    message="Loading specifications..."

                />

            </View>

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Error State                                                            */
    /* ---------------------------------------------------------------------- */

    if (error) {

        return (

            <View
                style={[

                    styles.container,

                    style,

                ]}
            >

                <ErrorState

                    title="Unable to load specifications"

                    description={
                        error?.message ??
                        "Please try again."
                    }

                    onRetry={
                        onRetry
                    }

                />

            </View>

        );

    }

    /* ---------------------------------------------------------------------- */
    /* Empty State                                                            */
    /* ---------------------------------------------------------------------- */

    if (!hasSpecifications) {

        return (

            <View
                style={[

                    styles.container,

                    style,

                ]}
            >

                <EmptyState

                    icon="clipboard-text-outline"

                    title="No Specifications"

                    description="Specifications are not available for this product."

                />

            </View>

        );

    }

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

            {/* ------------------------------------------------------------------ */}
            {/* Section Title                                                     */}
            {/* ------------------------------------------------------------------ */}

            <Text
                style={[

                    styles.title,

                    {

                        color:
                            colors.text,

                    },

                ]}
            >

                {title}

            </Text>

            {/* ------------------------------------------------------------------ */}
            {/* Specifications Table                                              */}
            {/* ------------------------------------------------------------------ */}

            <View
                style={[
                    styles.tableContainer,
                    {
                        borderColor:
                            colors.outline ??
                            "#E5E7EB",
                    },
                ]}
            >

                {/* ---------------------------------------------------------- */}
                {/* Grouped Specifications                                     */}
                {/* ---------------------------------------------------------- */}

                {grouped ? (

                    visibleSpecifications.map(

                        (section, sectionIndex) => (

                            <View
                                key={
                                    section.title ??
                                    sectionIndex
                                }
                            >

                                {!!section.title && (

                                    <Text
                                        style={[

                                            styles.groupTitle,

                                            {

                                                color:
                                                    colors.primary,

                                            },

                                        ]}
                                    >

                                        {section.title}

                                    </Text>

                                )}

                                {(section.items ?? []).map(

                                    (

                                        item,

                                        rowIndex,

                                    ) => {

                                        const isLastRow =
                                            rowIndex ===
                                            (section.items ?? []).length - 1;

                                        return (

                                            <View

                                                key={
                                                    `${sectionIndex}-${rowIndex}`
                                                }

                                                style={[

                                                    styles.row,

                                                    zebraRows &&
                                                    rowIndex % 2 === 1 && {

                                                        backgroundColor:
                                                            colors.surfaceVariant ??
                                                            colors.surface,

                                                    },

                                                    !isLastRow && {

                                                        borderBottomWidth:
                                                            StyleSheet.hairlineWidth,

                                                        borderBottomColor:
                                                            colors.outline ??
                                                            "#E5E7EB",

                                                    },

                                                ]}

                                            >

                                                <Text
                                                    style={[

                                                        styles.label,

                                                        {

                                                            color:
                                                                colors.textSecondary,

                                                        },

                                                    ]}
                                                >

                                                    {item.label}

                                                </Text>

                                                <Text
                                                    style={[

                                                        styles.value,

                                                        {

                                                            color:
                                                                colors.text,

                                                        },

                                                    ]}

                                                    numberOfLines={2}

                                                    ellipsizeMode="tail"
                                                >

                                                    {item.value}

                                                </Text>

                                            </View>

                                        );

                                    }

                                )}

                            </View>

                        )

                    )

                ) : (

                    visibleSpecifications.map(

                        (

                            item,

                            index,

                        ) => {

                            const isLastRow =
                                index === visibleSpecifications.length - 1;

                            return (

                                <View

                                    key={
                                        item.label ??
                                        index
                                    }

                                    style={[

                                        styles.row,

                                        zebraRows &&
                                        index % 2 === 1 && {

                                            backgroundColor:
                                                colors.surfaceVariant ??
                                                colors.surface,

                                        },

                                        !isLastRow && {

                                            borderBottomWidth:
                                                StyleSheet.hairlineWidth,

                                            borderBottomColor:
                                                colors.outline ??
                                                "#E5E7EB",

                                        },

                                    ]}

                                >

                                    <Text
                                        style={[

                                            styles.label,

                                            {

                                                color:
                                                    colors.textSecondary,

                                            },

                                        ]}
                                    >

                                        {item.label}

                                    </Text>

                                    <Text
                                        style={[

                                            styles.value,

                                            {

                                                color:
                                                    colors.text,

                                            },

                                        ]}

                                        numberOfLines={2}

                                        ellipsizeMode="tail"
                                    >

                                        {item.value}

                                    </Text>

                                </View>

                            );

                        }

                    )

                )}

            </View>

            {/* -------------------------------------------------------------- */}
            {/* Expand / Collapse                                              */}
            {/* -------------------------------------------------------------- */}

            {showToggle && (

                <>

                    <Divider
                        spacing={theme.spacing.md}
                    />

                    <TouchableOpacity

                        onPress={
                            handleToggle
                        }

                        activeOpacity={0.7}

                        accessibilityRole="button"

                        accessibilityLabel={
                            expanded
                                ? readLessLabel
                                : readMoreLabel
                        }

                        accessibilityHint={
                            expanded
                                ? "Collapse specifications"
                                : "Expand to see all specifications"
                        }

                        style={
                            styles.toggleButton
                        }

                    >

                        <Text
                            style={[

                                styles.toggleText,

                                {

                                    color:
                                        colors.primary,

                                },

                            ]}
                        >

                            {

                                expanded

                                    ? readLessLabel

                                    : readMoreLabel

                            }

                        </Text>

                    </TouchableOpacity>

                </>

            )}

        </View>

    );

});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

SpecificationTable.displayName =
    "SpecificationTable";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

SpecificationTable.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Content                                                                */
    /* ---------------------------------------------------------------------- */

    title:
        PropTypes.string,

    specifications:
        PropTypes.arrayOf(

            PropTypes.oneOfType([

                PropTypes.shape({

                    label:
                        PropTypes.string,

                    value:
                        PropTypes.oneOfType([

                            PropTypes.string,

                            PropTypes.number,

                            PropTypes.node,

                        ]),

                }),

                PropTypes.shape({

                    title:
                        PropTypes.string,

                    items:
                        PropTypes.arrayOf(

                            PropTypes.shape({

                                label:
                                    PropTypes.string,

                                value:
                                    PropTypes.oneOfType([

                                        PropTypes.string,

                                        PropTypes.number,

                                        PropTypes.node,

                                    ]),

                            })

                        ),

                }),

            ])

        ),

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    expandable:
        PropTypes.bool,

    collapsedRows:
        PropTypes.number,

    readMoreLabel:
        PropTypes.string,

    readLessLabel:
        PropTypes.string,

    zebraRows:
        PropTypes.bool,

    grouped:
        PropTypes.bool,

    /* ---------------------------------------------------------------------- */
    /* State                                                                  */
    /* ---------------------------------------------------------------------- */

    loading:
        PropTypes.bool,

    error:
        PropTypes.object,

    onRetry:
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
                theme.spacing.md,

        },

        /* ------------------------------------------------------------------ */
        /* Title                                                              */
        /* ------------------------------------------------------------------ */

        title: {

            fontSize:
                18,

            fontWeight:
                "700",

            marginBottom:
                theme.spacing.md,

        },

        /* ------------------------------------------------------------------ */
        /* Table                                                              */
        /* ------------------------------------------------------------------ */

        tableContainer: {

            borderWidth:
                1,

            borderRadius:
                12,

            overflow:
                "hidden",

        },

        row: {

            flexDirection:
                "row",

            justifyContent:
                "space-between",

            alignItems:
                "center",

            paddingHorizontal:
                theme.spacing.md,

            paddingVertical:
                14,

        },

        label: {

            flex:
                1,

            fontSize:
                14,

            fontWeight:
                "500",

            paddingRight:
                theme.spacing.sm,

        },

        value: {

            flex:
                1,

            fontSize:
                14,

            fontWeight:
                "600",

            textAlign:
                "right",

        },

        /* ------------------------------------------------------------------ */
        /* Groups                                                             */
        /* ------------------------------------------------------------------ */

        groupTitle: {

            fontSize:
                16,

            fontWeight:
                "700",

            paddingHorizontal:
                theme.spacing.md,

            paddingTop:
                theme.spacing.md,

            paddingBottom:
                theme.spacing.xs,

        },

        /* ------------------------------------------------------------------ */
        /* Toggle                                                             */
        /* ------------------------------------------------------------------ */

        toggleButton: {

            alignSelf:
                "center",

            paddingVertical:
                10,

        },

        toggleText: {

            fontSize:
                15,

            fontWeight:
                "600",

        },

    });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    SpecificationTable;