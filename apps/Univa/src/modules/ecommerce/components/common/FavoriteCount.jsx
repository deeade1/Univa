/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/FavoriteCount.jsx       */
/* -------------------------------------------------------------------------- */

import React, {
    memo,
    useMemo,
} from "react";

import PropTypes
    from "prop-types";

import IconLabel
    from "./IconLabel";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const formatCount = (
    value
) => {

    if (
        value == null
    ) {
        return "0";
    }

    if (
        value < 1000
    ) {
        return String(
            value
        );
    }

    if (
        value < 1000000
    ) {

        return (
            (
                value /
                1000
            )
                .toFixed(1)
                .replace(
                    ".0",
                    ""
                ) + "K"
        );

    }

    if (
        value <
        1000000000
    ) {

        return (
            (
                value /
                1000000
            )
                .toFixed(1)
                .replace(
                    ".0",
                    ""
                ) + "M"
        );

    }

    return (
        (
            value /
            1000000000
        )
            .toFixed(1)
            .replace(
                ".0",
                ""
            ) + "B"
    );

};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const FavoriteCount =
memo(({

    count = 0,

    active = false,

    hideWhenZero = false,

    showIcon = true,

    iconSize = 16,

    activeColor,

    inactiveColor,

    onPress,

    style,

    textStyle,

    iconStyle,

}) => {

    const {
        colors,
    } = theme;

    /* ---------------------------------------------------------------------- */
    /* Hide                                                                    */
    /* ---------------------------------------------------------------------- */

    if (
        hideWhenZero &&
        count <= 0
    ) {

        return null;

    }

    /* ---------------------------------------------------------------------- */
    /* Derived Values                                                          */
    /* ---------------------------------------------------------------------- */

    const label =
        useMemo(
            () =>
                formatCount(
                    count
                ),
            [
                count,
            ]
        );

    const iconName =
        active
            ? "heart"
            : "heart-outline";

    const iconColor =
        active

            ? (
                activeColor ??
                colors.error
            )

            : (
                inactiveColor ??
                colors.textSecondary
            );

    /* ---------------------------------------------------------------------- */
    /* Render                                                                  */
    /* ---------------------------------------------------------------------- */

    return (

        <IconLabel

            icon={
                showIcon
                    ? iconName
                    : undefined
            }

            label={label}

            size={
                iconSize
            }

            color={
                iconColor
            }

            textColor={
                colors.text
            }

            onPress={
                onPress
            }

            style={
                style
            }

            textStyle={
                textStyle
            }

            iconStyle={
                iconStyle
            }

        />

    );

});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

FavoriteCount.displayName =
    "FavoriteCount";

/* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

FavoriteCount.propTypes = {

    /* ---------------------------------------------------------------------- */
    /* Data                                                                    */
    /* ---------------------------------------------------------------------- */

    count:
        PropTypes.number,

    active:
        PropTypes.bool,

    hideWhenZero:
        PropTypes.bool,

    /* ---------------------------------------------------------------------- */
    /* Appearance                                                              */
    /* ---------------------------------------------------------------------- */

    showIcon:
        PropTypes.bool,

    iconSize:
        PropTypes.number,

    activeColor:
        PropTypes.string,

    inactiveColor:
        PropTypes.string,

    /* ---------------------------------------------------------------------- */
    /* Events                                                                  */
    /* ---------------------------------------------------------------------- */

    onPress:
        PropTypes.func,

    /* ---------------------------------------------------------------------- */
    /* Styles                                                                  */
    /* ---------------------------------------------------------------------- */

    style:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

    textStyle:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

    iconStyle:
        PropTypes.oneOfType([
            PropTypes.object,
            PropTypes.array,
        ]),

};

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default
    FavoriteCount;