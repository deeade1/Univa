/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product/ProductDescription.jsx */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useState,
    useMemo,
    useCallback,
    useEffect,
} from "react";

import {
    StyleSheet,
    Text,
    Pressable,
    View,
} from "react-native";

import PropTypes from "prop-types";

import {
    colors,
    spacing,
    typography,
    radius,
} from "@/theme";

/* -------------------------------------------------------------------------- */
/* Common Components                                                          */
/* -------------------------------------------------------------------------- */

import Divider from "../common/Divider";
import LoadingOverlay from "../common/LoadingOverlay";
import EmptyState from "../common/EmptyState";
import ErrorState from "../common/ErrorState";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductDescription = memo(({
    /* ---------------------------------------------------------------------- */
    /* Content                                                                */
    /* ---------------------------------------------------------------------- */

    title = "Description",
    description = "",

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    expandable = true,
    collapsedLines = 4,
    readMoreLabel = "Read More",
    readLessLabel = "Read Less",
    showDivider = true,

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
    const themeColors = colors;
    const themeSpacing = spacing;

    /* ---------------------------------------------------------------------- */
    /* Local State                                                            */
    /* ---------------------------------------------------------------------- */

    const [expanded, setExpanded] = useState(false);
    const [isTruncated, setIsTruncated] = useState(false);

    /* ---------------------------------------------------------------------- */
    /* Computed Values                                                        */
    /* ---------------------------------------------------------------------- */

    const hasDescription = Boolean(description?.trim());

    const showToggle = expandable && hasDescription && isTruncated;

    /* ---------------------------------------------------------------------- */
    /* Effects                                                                */
    /* ---------------------------------------------------------------------- */

    // Reset truncation when description changes
    useEffect(() => {
        setExpanded(false);
        setIsTruncated(false);
    }, [description]);

    /* ---------------------------------------------------------------------- */
    /* Handlers                                                               */
    /* ---------------------------------------------------------------------- */

    const handleToggle = useCallback(() => {
        setExpanded((previous) => !previous);
    }, []);

    /* ---------------------------------------------------------------------- */
    /* Text Layout Callback - Detect if text is truncated                     */
    /* ---------------------------------------------------------------------- */

    const handleTextLayout = useCallback(
        (event) => {
            // Only check if expandable is enabled
            if (!expandable) {
                return;
            }

            const { lines } = event.nativeEvent;

            // Check if text has more lines than collapsedLines
            setIsTruncated(lines.length > collapsedLines);
        },
        [expandable, collapsedLines]
    );

    /* ---------------------------------------------------------------------- */
    /* Loading State                                                          */
    /* ---------------------------------------------------------------------- */

    if (loading) {
        return (
            <View style={[styles.container, style]}>
                <LoadingOverlay
                    visible
                    fullscreen={false}
                    transparent
                    message="Loading description..."
                />
            </View>
        );
    }

    /* ---------------------------------------------------------------------- */
    /* Error State                                                            */
    /* ---------------------------------------------------------------------- */

    if (error) {
        return (
            <View style={[styles.container, style]}>
                <ErrorState
                    title="Unable to load description"
                    description={error?.message ?? "Please try again."}
                    onRetry={onRetry}
                />
            </View>
        );
    }

    /* ---------------------------------------------------------------------- */
    /* Empty State                                                            */
    /* ---------------------------------------------------------------------- */

    if (!hasDescription) {
        return (
            <View style={[styles.container, style]}>
                <EmptyState
                    icon="text-box-outline"
                    title="No Description"
                    description="This product has no description available."
                />
            </View>
        );
    }

    /* ---------------------------------------------------------------------- */
    /* Component                                                              */
    /* ---------------------------------------------------------------------- */

    return (
        <View style={[styles.container, style]}>
            {/* ------------------------------------------------------------------ */}
            {/* Title                                                             */}
            {/* ------------------------------------------------------------------ */}

            <Text
                style={[
                    styles.title,
                    {
                        color: themeColors.text,
                    },
                ]}
            >
                {title}
            </Text>

            {/* ------------------------------------------------------------------ */}
            {/* Description                                                       */}
            {/* ------------------------------------------------------------------ */}

            <Text
                style={[
                    styles.description,
                    {
                        color: themeColors.textSecondary,
                    },
                ]}
                numberOfLines={expanded ? undefined : collapsedLines}
                onTextLayout={handleTextLayout}
            >
                {description}
            </Text>

            {showDivider && <Divider spacing={themeSpacing.md} />}

            {/* ------------------------------------------------------------------ */}
            {/* Read More / Read Less                                             */}
            {/* ------------------------------------------------------------------ */}

            {showToggle && (
                <Pressable
                    onPress={handleToggle}
                    accessibilityRole="button"
                    accessibilityLabel={expanded ? readLessLabel : readMoreLabel}
                    accessibilityHint={
                        expanded
                            ? "Collapse product description"
                            : "Expand product description"
                    }
                    style={styles.toggleButton}
                >
                    <Text
                        style={[
                            styles.toggleText,
                            {
                                color: themeColors.primary,
                            },
                        ]}
                    >
                        {expanded ? readLessLabel : readMoreLabel}
                    </Text>
                </Pressable>
            )}
        </View>
    );
});

/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

ProductDescription.displayName = "ProductDescription";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

ProductDescription.propTypes = {
    /* ---------------------------------------------------------------------- */
    /* Content                                                                */
    /* ---------------------------------------------------------------------- */

    title: PropTypes.string,

    description: PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Display                                                                */
    /* ---------------------------------------------------------------------- */

    expandable: PropTypes.bool,

    collapsedLines: PropTypes.number,

    readMoreLabel: PropTypes.string,

    readLessLabel: PropTypes.string,

    showDivider: PropTypes.bool,

    /* ---------------------------------------------------------------------- */
    /* State                                                                  */
    /* ---------------------------------------------------------------------- */

    loading: PropTypes.bool,

    error: PropTypes.shape({
        message: PropTypes.string,
    }),

    /* ---------------------------------------------------------------------- */
    /* Events                                                                 */
    /* ---------------------------------------------------------------------- */

    onRetry: PropTypes.func,

    /* ---------------------------------------------------------------------- */
    /* Styling                                                                */
    /* ---------------------------------------------------------------------- */

    style: PropTypes.oneOfType([
        PropTypes.object,
        PropTypes.array,
    ]),
};

/* -------------------------------------------------------------------------- */
/* Default Props                                                              */
/* -------------------------------------------------------------------------- */

ProductDescription.defaultProps = {
    title: "Description",
    description: "",
    expandable: true,
    collapsedLines: 4,
    readMoreLabel: "Read More",
    readLessLabel: "Read Less",
    showDivider: true,
    loading: false,
    error: null,
    onRetry: null,
    style: null,
};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles = StyleSheet.create({
    /* ------------------------------------------------------------------ */
    /* Container                                                          */
    /* ------------------------------------------------------------------ */

    container: {
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.md,
    },

    /* ------------------------------------------------------------------ */
    /* Title                                                              */
    /* ------------------------------------------------------------------ */

    title: {
        fontSize: typography.fontSize.lg,
        fontWeight: typography.fontWeight.bold,
        marginBottom: spacing.md,
    },

    /* ------------------------------------------------------------------ */
    /* Description                                                        */
    /* ------------------------------------------------------------------ */

    description: {
        fontSize: typography.fontSize.md,
        lineHeight: 24,
    },

    /* ------------------------------------------------------------------ */
    /* Toggle                                                             */
    /* ------------------------------------------------------------------ */

    toggleButton: {
        alignSelf: "flex-start",
        paddingVertical: spacing.xs,
    },

    toggleText: {
        fontSize: typography.fontSize.md,
        fontWeight: typography.fontWeight.semibold,
    },
});

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default ProductDescription;