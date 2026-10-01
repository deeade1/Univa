/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/common/CountdownTimer.jsx      */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  StyleSheet,
  Text,
  View,
} from "react-native";

import PropTypes from "prop-types";

import { Ionicons } from "@expo/vector-icons";

import theme from "@/theme"

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const DEFAULT_INTERVAL = 1000;

const DEFAULT_SEPARATOR = ":";

const DEFAULT_EXPIRED_TEXT =
  "Expired";

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

const pad = (value) =>
  String(value).padStart(2, "0");

const calculateRemaining = (
  target
) => {

  const now =
    Date.now();

  const remaining =
    Math.max(
      0,
      target - now
    );

  const days =
    Math.floor(
      remaining /
      86400000
    );

  const hours =
    Math.floor(
      (
        remaining %
        86400000
      ) /
      3600000
    );

  const minutes =
    Math.floor(
      (
        remaining %
        3600000
      ) /
      60000
    );

  const seconds =
    Math.floor(
      (
        remaining %
        60000
      ) /
      1000
    );

  return {

    remaining,

    days,

    hours,

    minutes,

    seconds,

    expired:
      remaining === 0,

  };

};

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const CountdownTimer = memo(({

  expiresAt,

  interval =
    DEFAULT_INTERVAL,

  separator =
    DEFAULT_SEPARATOR,

  showDays = true,

  showHours = true,

  showMinutes = true,

  showSeconds = true,

  showIcon = true,

  autoHide = false,

  expiredText =
    DEFAULT_EXPIRED_TEXT,

  onExpire,

  style,

  textStyle,

  iconColor,

}) => {

  const { colors } = theme();

  const target =
    useMemo(() => {

      if (
        expiresAt instanceof Date
      ) {
        return expiresAt.getTime();
      }

      return new Date(
        expiresAt
      ).getTime();

    }, [expiresAt]);

  const expiredCalled =
    useRef(false);

  const [

    time,

    setTime,

  ] = useState(
    calculateRemaining(
      target
    )
  );

  /* ---------------------------------------------------------------------- */
  /* Timer                                                                   */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {

    const id =
      setInterval(() => {

        const next =
          calculateRemaining(
            target
          );

        setTime(next);

      }, interval);

    return () =>
      clearInterval(id);

  }, [
    target,
    interval,
  ]);

  /* ---------------------------------------------------------------------- */
  /* Expired Callback                                                        */
  /* ---------------------------------------------------------------------- */

  useEffect(() => {

    if (
      time.expired &&
      !expiredCalled.current
    ) {

      expiredCalled.current =
        true;

      onExpire?.();

    }

  }, [
    time.expired,
    onExpire,
  ]);
    /* ---------------------------------------------------------------------- */
  /* Auto Hide                                                               */
  /* ---------------------------------------------------------------------- */

  if (
    autoHide &&
    time.expired
  ) {
    return null;
  }

  /* ---------------------------------------------------------------------- */
  /* Expired                                                                 */
  /* ---------------------------------------------------------------------- */

  if (
    time.expired
  ) {
    return (
      <View
        style={[
          styles.container,
          style,
        ]}
      >
        {showIcon && (
          <Ionicons
            name="time-outline"
            size={16}
            color={
              iconColor ??
              colors.error
            }
          />
        )}

        <Text
          style={[
            styles.expiredText,
            {
              color:
                colors.error,
            },
            textStyle,
          ]}
        >
          {expiredText}
        </Text>
      </View>
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Segments                                                                */
  /* ---------------------------------------------------------------------- */

  const segments = [];

  if (showDays) {
    segments.push(
      pad(time.days)
    );
  }

  if (showHours) {
    segments.push(
      pad(time.hours)
    );
  }

  if (showMinutes) {
    segments.push(
      pad(time.minutes)
    );
  }

  if (showSeconds) {
    segments.push(
      pad(time.seconds)
    );
  }

  /* ---------------------------------------------------------------------- */
  /* Render                                                                  */
  /* ---------------------------------------------------------------------- */

  return (
    <View
      style={[
        styles.container,
        style,
      ]}
    >
      {showIcon && (
        <Ionicons
          name="time-outline"
          size={16}
          color={
            iconColor ??
            colors.primary
          }
          style={
            styles.icon
          }
        />
      )}

      <Text
        style={[
          styles.time,
          {
            color:
              colors.text,
          },
          textStyle,
        ]}
      >
        {segments.join(
          separator
        )}
      </Text>
    </View>
  );
});
/* -------------------------------------------------------------------------- */
/* Display Name                                                               */
/* -------------------------------------------------------------------------- */

CountdownTimer.displayName =
  "CountdownTimer";

/* -------------------------------------------------------------------------- */
/* Prop Types                                                                 */
/* -------------------------------------------------------------------------- */

CountdownTimer.propTypes = {

  expiresAt:
    PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
      PropTypes.instanceOf(Date),
    ]).isRequired,

  interval:
    PropTypes.number,

  separator:
    PropTypes.string,

  showDays:
    PropTypes.bool,

  showHours:
    PropTypes.bool,

  showMinutes:
    PropTypes.bool,

  showSeconds:
    PropTypes.bool,

  showIcon:
    PropTypes.bool,

  autoHide:
    PropTypes.bool,

  expiredText:
    PropTypes.string,

  onExpire:
    PropTypes.func,

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

  iconColor:
    PropTypes.string,

};

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({

    container: {

      flexDirection:
        "row",

      alignItems:
        "center",

      justifyContent:
        "center",

    },

    icon: {

      marginRight: 6,

    },

    time: {

      fontSize: 14,

      fontWeight:
        "700",

      fontVariant: [
        "tabular-nums",
      ],

      letterSpacing:
        0.4,

    },

    expiredText: {

      marginLeft: 6,

      fontSize: 14,

      fontWeight:
        "600",

    },

  });

/* -------------------------------------------------------------------------- */
/* Export                                                                     */
/* -------------------------------------------------------------------------- */

export default CountdownTimer;