/* -------------------------------------------------------------------------- */
/* apps/Univa/src/modules/ecommerce/components/reviews/ReviewImages.jsx       */
/* -------------------------------------------------------------------------- */

import React, {
  memo,
  useMemo,
  useState,
  useCallback,
} from "react";

import {
  View,
  Text,
  Image,
  Pressable,
  Modal,
  FlatList,
  Dimensions,
  StyleSheet,
} from "react-native";

import { MaterialCommunityIcons } from "@expo/vector-icons";


import theme from "@/theme"

/* -------------------------------------------------------------------------- */

const { width, height } =
  Dimensions.get("window");

/* -------------------------------------------------------------------------- */

const ReviewImages = memo(
  ({
    images = [],

    imageSize = 84,

    spacing = 10,

    maxVisible = 4,

    rounded = 12,

    showCounter = true,

    style,
  }) => {
    const { colors } = theme;

    const [visible, setVisible] =
      useState(false);

    const [currentIndex, setCurrentIndex] =
      useState(0);

    const visibleImages =
      useMemo(
        () =>
          images.slice(
            0,
            maxVisible
          ),
        [images, maxVisible]
      );

    const openImage =
      useCallback((index) => {
        setCurrentIndex(index);
        setVisible(true);
      }, []);

    const closeViewer =
      useCallback(() => {
        setVisible(false);
      }, []);

    const renderThumbnail = ({
      item,
      index,
    }) => {
      const remainingImages =
        images.length -
        maxVisible;

      const isLast =
        index ===
          maxVisible - 1 &&
        images.length >
          maxVisible;

      return (
        <Pressable
          onPress={() =>
            openImage(index)
          }
          style={{
            marginRight:
              spacing,
          }}
        >
          <Image
            source={{
              uri: item,
            }}
            resizeMode="cover"
            style={[
              styles.thumbnail,
              {
                width:
                  imageSize,

                height:
                  imageSize,

                borderRadius:
                  rounded,
              },
            ]}
          />

          {isLast &&
            showCounter && (
              <View
                style={[
                  styles.overlay,
                  {
                    borderRadius:
                      rounded,
                  },
                ]}
              >
                <MaterialCommunityIcons
                  name="image-multiple"
                  size={24}
                  color="#FFFFFF"
                />

                <Text
                  style={
                    styles.counterText
                  }
                >
                  +
                  {
                    remainingImages
                  }
                </Text>
              </View>
            )}
        </Pressable>
      );
    };

    return (
      <>
        <FlatList
          horizontal
          data={visibleImages}
          renderItem={
            renderThumbnail
          }
          keyExtractor={(
            item,
            index
          ) =>
            `${item}-${index}`
          }
          showsHorizontalScrollIndicator={
            false
          }
          style={style}
        />

        {/* ---------------------------------------------------------- */}
        {/* Full Screen Viewer */}
        {/* ---------------------------------------------------------- */}

        <Modal
          visible={visible}
          transparent={
            false
          }
          animationType="fade"
          onRequestClose={
            closeViewer
          }
        >
          <View
            style={[
              styles.viewer,
              {
                backgroundColor:
                  "#000",
              },
            ]}
          >
            <Pressable
              onPress={
                closeViewer
              }
              style={
                styles.closeButton
              }
            >
              <MaterialCommunityIcons
                name="close"
                size={32}
                color="#FFFFFF"
              />
            </Pressable>

            <FlatList
              horizontal
              pagingEnabled
              data={images}
              initialScrollIndex={
                currentIndex
              }
              keyExtractor={(
                item,
                index
              ) =>
                `${item}-${index}`
              }
              getItemLayout={(
                _,
                index
              ) => ({
                length:
                  width,
                offset:
                  width *
                  index,
                index,
              })}
              showsHorizontalScrollIndicator={
                false
              }
              renderItem={({
                item,
              }) => (
                <View
                  style={
                    styles.page
                  }
                >
                  <Image
                    source={{
                      uri: item,
                    }}
                    resizeMode="contain"
                    style={
                      styles.fullImage
                    }
                  />
                </View>
              )}
            />
          </View>
        </Modal>
      </>
    );
  }
);

ReviewImages.displayName =
  "ReviewImages";

/* -------------------------------------------------------------------------- */
/* Styles                                                                     */
/* -------------------------------------------------------------------------- */

const styles =
  StyleSheet.create({
    thumbnail: {
      backgroundColor:
        "#E5E7EB",
    },

    overlay: {
      ...StyleSheet.absoluteFillObject,

      backgroundColor:
        "rgba(0,0,0,0.45)",

      justifyContent:
        "center",

      alignItems:
        "center",
    },

    counterText: {
      marginTop: 6,

      color: "#FFFFFF",

      fontSize: 20,

      fontWeight: "700",
    },

    viewer: {
      flex: 1,
    },

    closeButton: {
      position: "absolute",

      top: 50,

      right: 20,

      zIndex: 100,

      padding: 8,
    },

    page: {
      width,

      height,

      justifyContent:
        "center",

      alignItems:
        "center",
    },

    fullImage: {
      width:
        width - 24,

      height:
        height * 0.8,
    },
  });

export default ReviewImages;