/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/product-details/               */
/* ProductShareSheet.jsx                                                      */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useCallback,
} from "react";

import PropTypes from "prop-types";

import {
  View,
  Text,
  Pressable,
  StyleSheet,
  Share,
  Alert,
} from "react-native";

import BottomSheet, {
  BottomSheetScrollView,
} from "@gorhom/bottom-sheet";

import * as Clipboard from "expo-clipboard";

import {
  MaterialCommunityIcons,
} from "@expo/vector-icons";

import theme from "@/theme";

/* -------------------------------------------------------------------------- */
/* Share Option                                                               */
/* -------------------------------------------------------------------------- */

const ShareOption = memo(
  ({
    icon,
    title,
    color,
    onPress,
  }) => (
    <Pressable
      onPress={onPress}
      style={styles.option}
    >
      <View
        style={[
          styles.optionIcon,
          {
            backgroundColor:
              color + "18",
          },
        ]}
      >
        <MaterialCommunityIcons
          name={icon}
          size={26}
          color={color}
        />
      </View>

      <Text
        style={styles.optionTitle}
      >
        {title}
      </Text>
    </Pressable>
  )
);

ShareOption.displayName =
  "ShareOption";

/* -------------------------------------------------------------------------- */
/* Component                                                                  */
/* -------------------------------------------------------------------------- */

const ProductShareSheet =
  memo(
    ({
      sheetRef,

      visible,

      product,

      productUrl,

      snapPoints = [
        "55%",
      ],

      onClose,

      onShare,

      style,
    }) => {
      const { colors } =
        theme;

      /* ------------------------------------------------------------------ */
      /* Share Message                                                      */
      /* ------------------------------------------------------------------ */

      const shareMessage =
        useMemo(() => {
          return `${product?.name}

${product?.price ?? ""}

${productUrl}`;
        }, [
          product,
          productUrl,
        ]);

      /* ------------------------------------------------------------------ */
      /* Native Share                                                       */
      /* ------------------------------------------------------------------ */

      const handleNativeShare =
        useCallback(
          async () => {
            try {
              await Share.share({
                message:
                  shareMessage,

                url:
                  productUrl,
              });

              onShare?.(
                "native"
              );
            } catch (error) {
              console.warn(
                error
              );
            }
          },
          [
            shareMessage,
            productUrl,
            onShare,
          ]
        );

      /* ------------------------------------------------------------------ */
      /* Copy Link                                                          */
      /* ------------------------------------------------------------------ */

      const handleCopy =
        useCallback(
          async () => {
            await Clipboard.setStringAsync(
              productUrl
            );

            Alert.alert(
              "Copied",
              "Product link copied to clipboard."
            );

            onShare?.(
              "copy"
            );
          },
          [
            productUrl,
            onShare,
          ]
        );

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
                  Share Product
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
                  Share this product
                  with friends and
                  family
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
            {/* Product Preview                                            */}
            {/* ---------------------------------------------------------- */}

            <View
              style={[
                styles.productCard,
                {
                  borderColor:
                    colors.border,
                },
              ]}
            >
              <Text
                style={[
                  styles.productName,
                  {
                    color:
                      colors.text,
                  },
                ]}
                numberOfLines={2}
              >
                {product?.name ??
                  "Product"}
              </Text>

              {!!product?.price && (
                <Text
                  style={[
                    styles.productPrice,
                    {
                      color:
                        colors.primary,
                    },
                  ]}
                >
                  {product.price}
                </Text>
              )}

              {!!productUrl && (
                <Text
                  numberOfLines={1}
                  style={[
                    styles.productLink,
                    {
                      color:
                        colors.textSecondary,
                      },
                    ]}
                >
                  {productUrl}
                </Text>
              )}
            </View>

            {/* ---------------------------------------------------------- */}
            {/* Share Options                                              */}
            {/* ---------------------------------------------------------- */}

            <View
              style={
                styles.optionsGrid
              }
            >
              <ShareOption
                title="Share"
                icon="share-variant"
                color={
                  colors.primary
                }
                onPress={
                  handleNativeShare
                }
              />

              <ShareOption
                title="Copy Link"
                icon="content-copy"
                color="#1976D2"
                onPress={
                  handleCopy
                }
              />

              <ShareOption
                title="WhatsApp"
                icon="whatsapp"
                color="#25D366"
                onPress={() =>
                  onShare?.(
                    "whatsapp"
                  )
                }
              />

              <ShareOption
                title="Facebook"
                icon="facebook"
                color="#1877F2"
                onPress={() =>
                  onShare?.(
                    "facebook"
                  )
                }
              />

              <ShareOption
                title="X"
                icon="twitter"
                color="#000000"
                onPress={() =>
                  onShare?.(
                    "x"
                  )
                }
              />

              <ShareOption
                title="Telegram"
                icon="send"
                color="#229ED9"
                onPress={() =>
                  onShare?.(
                    "telegram"
                  )
                }
              />

              <ShareOption
                title="Email"
                icon="email-outline"
                color="#EA4335"
                onPress={() =>
                  onShare?.(
                    "email"
                  )
                }
              />

              <ShareOption
                title="QR Code"
                icon="qrcode"
                color="#6A1B9A"
                onPress={() =>
                  onShare?.(
                    "qr"
                  )
                }
              />
            </View>

            {/* ---------------------------------------------------------- */}
            {/* Share Information                                          */}
            {/* ---------------------------------------------------------- */}

            <View
              style={[
                styles.infoCard,
                {
                  backgroundColor:
                    colors.background,
                },
              ]}
            >
              <MaterialCommunityIcons
                name="information-outline"
                size={18}
                color={
                  colors.primary
                }
              />

              <Text
                style={[
                  styles.infoText,
                  {
                    color:
                      colors.textSecondary,
                  },
                ]}
              >
                Share this product
                with friends or
                family. Sharing the
                product link lets
                others open the
                product directly in
                the Univa app or on
                the web.
              </Text>
            </View>
                        {/* ---------------------------------------------------------- */}
            {/* Recent Share Targets                                       */}
            {/* ---------------------------------------------------------- */}

            <View
              style={
                styles.section
              }
            >
              <Text
                style={[
                  styles.sectionTitle,
                  {
                    color:
                      colors.text,
                  },
                ]}
              >
                Suggested Sharing
              </Text>

              <View
                style={
                  styles.recentContainer
                }
              >
                {[
                  {
                    icon:
                      "account-circle",
                    label:
                      "Friends",
                  },
                  {
                    icon:
                      "account-group",
                    label:
                      "Family",
                  },
                  {
                    icon:
                      "briefcase-account",
                    label:
                      "Work",
                  },
                  {
                    icon:
                      "star-circle",
                    label:
                      "Favorites",
                  },
                ].map(
                  (
                    item
                  ) => (
                    <Pressable
                      key={
                        item.label
                      }
                      style={
                        styles.recentItem
                      }
                      onPress={() =>
                        onShare?.(
                          item.label.toLowerCase()
                        )
                      }
                    >
                      <View
                        style={[
                          styles.recentIcon,
                          {
                            backgroundColor:
                              colors.primary +
                              "18",
                          },
                        ]}
                      >
                        <MaterialCommunityIcons
                          name={
                            item.icon
                          }
                          size={24}
                          color={
                            colors.primary
                          }
                        />
                      </View>

                      <Text
                        style={[
                          styles.recentLabel,
                          {
                            color:
                              colors.text,
                          },
                        ]}
                      >
                        {
                          item.label
                        }
                      </Text>
                    </Pressable>
                  )
                )}
              </View>
            </View>

            {/* ---------------------------------------------------------- */}
            {/* Referral Card                                              */}
            {/* ---------------------------------------------------------- */}

            <View
              style={[
                styles.referralCard,
                {
                  backgroundColor:
                    colors.primary +
                    "12",
                },
              ]}
            >
              <MaterialCommunityIcons
                name="gift-outline"
                size={34}
                color={
                  colors.primary
                }
              />

              <View
                style={
                  styles.referralContent
                }
              >
                <Text
                  style={[
                    styles.referralTitle,
                    {
                      color:
                        colors.text,
                    },
                  ]}
                >
                  Invite Friends
                </Text>

                <Text
                  style={[
                    styles.referralDescription,
                    {
                      color:
                        colors.textSecondary,
                    },
                  ]}
                >
                  Share products with
                  friends and invite
                  them to join Univa.
                  Referral rewards can
                  be integrated here in
                  the future.
                </Text>
              </View>
            </View>

            {/* ---------------------------------------------------------- */}
            {/* Footer Actions                                             */}
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
                style={[
                  styles.secondaryButton,
                  {
                    borderColor:
                      colors.border,
                  },
                ]}
                onPress={
                  onClose
                }
              >
                <Text
                  style={[
                    styles.secondaryText,
                    {
                      color:
                        colors.text,
                    },
                  ]}
                >
                  Cancel
                </Text>
              </Pressable>

              <Pressable
                style={[
                  styles.primaryButton,
                  {
                    backgroundColor:
                      colors.primary,
                  },
                ]}
                onPress={
                  handleNativeShare
                }
              >
                <MaterialCommunityIcons
                  name="share-variant"
                  size={20}
                  color="#FFFFFF"
                />

                <Text
                  style={
                    styles.primaryText
                  }
                >
                  Share Now
                </Text>
              </Pressable>
            </View>
          </BottomSheetScrollView>
        </BottomSheet>
      );
    }
);

ProductShareSheet.displayName =
  "ProductShareSheet";
  /* -------------------------------------------------------------------------- */
/* PropTypes                                                                  */
/* -------------------------------------------------------------------------- */

const productShape =
  PropTypes.shape({
    id: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
    ]),

    name:
      PropTypes.string,

    price:
      PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
      ]),

    image:
      PropTypes.string,
  });

ShareOption.propTypes = {
  icon:
    PropTypes.string
      .isRequired,

  title:
    PropTypes.string
      .isRequired,

  color:
    PropTypes.string
      .isRequired,

  onPress:
    PropTypes.func
      .isRequired,
};

ProductShareSheet.propTypes = {
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

  productUrl:
    PropTypes.string,

  snapPoints:
    PropTypes.arrayOf(
      PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.number,
      ])
    ),

  onClose:
    PropTypes.func,

  onShare:
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

ProductShareSheet.defaultProps =
  {
    sheetRef: null,

    visible: false,

    product: null,

    productUrl: "",

    snapPoints: [
      "55%",
    ],

    onClose: null,

    onShare: null,

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
    /* Product Preview                                                    */
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

    productPrice: {
      marginTop: 8,

      fontSize: 20,

      fontWeight: "700",
    },

    productLink: {
      marginTop: 8,

      fontSize: 12,
    },

    /* ------------------------------------------------------------------ */
    /* Share Options                                                      */
    /* ------------------------------------------------------------------ */

    optionsGrid: {
      flexDirection: "row",

      flexWrap: "wrap",

      justifyContent:
        "space-between",

      marginBottom: 24,
    },

    option: {
      width: "23%",

      alignItems: "center",

      marginBottom: 20,
    },

    optionIcon: {
      width: 64,

      height: 64,

      borderRadius: 32,

      justifyContent:
        "center",

      alignItems:
        "center",

      marginBottom: 8,
    },

    optionTitle: {
      textAlign: "center",

      fontSize: 12,

      fontWeight: "600",
    },

    /* ------------------------------------------------------------------ */
    /* Info Card                                                          */
    /* ------------------------------------------------------------------ */

    infoCard: {
      flexDirection: "row",

      alignItems:
        "flex-start",

      borderRadius: 14,

      padding: 16,

      marginBottom: 24,
    },

    infoText: {
      flex: 1,

      marginLeft: 10,

      fontSize: 13,

      lineHeight: 20,
    },

    /* ------------------------------------------------------------------ */
    /* Suggested Sharing                                                  */
    /* ------------------------------------------------------------------ */

    section: {
      marginBottom: 24,
    },

    sectionTitle: {
      fontSize: 16,

      fontWeight: "700",

      marginBottom: 14,
    },

    recentContainer: {
      flexDirection: "row",

      justifyContent:
        "space-between",
    },

    recentItem: {
      alignItems:
        "center",
    },

    recentIcon: {
      width: 54,

      height: 54,

      borderRadius: 27,

      justifyContent:
        "center",

      alignItems:
        "center",

      marginBottom: 8,
    },

    recentLabel: {
      fontSize: 12,

      fontWeight: "600",
    },

    /* ------------------------------------------------------------------ */
    /* Referral Card                                                      */
    /* ------------------------------------------------------------------ */

    referralCard: {
      flexDirection: "row",

      borderRadius: 16,

      padding: 18,

      marginBottom: 24,
    },

    referralContent: {
      flex: 1,

      marginLeft: 14,
    },

    referralTitle: {
      fontSize: 16,

      fontWeight: "700",
    },

    referralDescription: {
      marginTop: 6,

      fontSize: 13,

      lineHeight: 20,
    },

    /* ------------------------------------------------------------------ */
    /* Footer                                                             */
    /* ------------------------------------------------------------------ */

    footer: {
      flexDirection: "row",

      borderTopWidth: 1,

      paddingTop: 20,
    },

    secondaryButton: {
      flex: 1,

      borderWidth: 1,

      borderRadius: 14,

      justifyContent:
        "center",

      alignItems:
        "center",

      paddingVertical: 14,

      marginRight: 10,
    },

    secondaryText: {
      fontSize: 15,

      fontWeight: "600",
    },

    primaryButton: {
      flex: 2,

      flexDirection: "row",

      justifyContent:
        "center",

      alignItems:
        "center",

      borderRadius: 14,

      paddingVertical: 14,
    },

    primaryText: {
      marginLeft: 8,

      color: "#FFFFFF",

      fontSize: 15,

      fontWeight: "700",
    },
  });

export default ProductShareSheet;