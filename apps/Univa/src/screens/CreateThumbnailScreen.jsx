import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  Image,
  Alert,
  FlatList,
  ScrollView,
  ActivityIndicator,
} from "react-native";
import { useQuery, useMutation } from "@apollo/client";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";

import {
  GET_THUMBNAILS,
  THUMBNAIL_CREATE,
  THUMBNAIL_DELETE,
} from "@/graphql/queries/mediaQuery/mutations/thumbnail";

export default function ThumbnailManagerScreen() {
  const [filters, setFilters] = useState({
    categoryId: "",
    collectionId: "",
    productMediaId: "",
    userId: "",
  });
  const [image, setImage] = useState(null);
  const [formData, setFormData] = useState({
    size: "",
    format: "",
    category: "",
    collection: "",
    productMedia: "",
    user: "",
  });

  const { data, loading, refetch } = useQuery(GET_THUMBNAILS, {
    variables: filters,
  });
  const [createThumbnail, { loading: creating }] = useMutation(THUMBNAIL_CREATE);
  const [deleteThumbnail, { loading: deleting }] = useMutation(THUMBNAIL_DELETE);

  const handlePickImage = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert("Permission Required", "Please allow access to photos.");
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    });

    if (!result.canceled) setImage(result.assets[0]);
  };

  const handleChange = (key, value) =>
    setFormData((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async () => {
    if (!image) {
      Alert.alert("Validation", "Please select an image first");
      return;
    }

    try {
      const file = {
        uri: image.uri,
        type: "image/jpeg",
        name: image.fileName || "thumbnail.jpg",
      };

      const variables = {
        input: {
          image: file,
          size: parseInt(formData.size) || 300,
          format: formData.format || "JPEG",
          category: formData.category || null,
          collection: formData.collection || null,
          productMedia: formData.productMedia || null,
          user: formData.user || null,
        },
      };

      const { data } = await createThumbnail({ variables });
      if (data.thumbnailCreate.errors?.length) {
        Alert.alert("Error", data.thumbnailCreate.errors[0].message);
      } else {
        Alert.alert("Success", "Thumbnail created successfully!");
        setFormData({
          size: "",
          format: "",
          category: "",
          collection: "",
          productMedia: "",
          user: "",
        });
        setImage(null);
        refetch();
      }
    } catch (err) {
      console.error(err);
      Alert.alert("Error", err.message);
    }
  };

  const handleDelete = async (id) => {
    Alert.alert("Confirm Delete", "Are you sure you want to delete this thumbnail?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            const { data } = await deleteThumbnail({ variables: { id } });
            if (data.thumbnailDelete.success) {
              Alert.alert("Deleted", "Thumbnail removed successfully");
              refetch();
            } else {
              Alert.alert("Error", "Failed to delete thumbnail");
            }
          } catch (err) {
            console.error(err);
          }
        },
      },
    ]);
  };

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const applyFilters = () => refetch(filters);

  const renderItem = ({ item }) => (
    <View
      style={{
        marginBottom: 12,
        borderWidth: 1,
        borderColor: "#ddd",
        borderRadius: 10,
        overflow: "hidden",
      }}
    >
      <Image
        source={{ uri: item.image?.url }}
        style={{ width: "100%", height: 140 }}
        resizeMode="cover"
      />
      <View style={{ padding: 10 }}>
        <Text style={{ fontWeight: "bold" }}>Format: {item.format}</Text>
        <Text>Size: {item.size}px</Text>
        <Text>Category: {item.category?.name || "—"}</Text>
        <Text>User: {item.user?.firstName || "—"}</Text>

        <TouchableOpacity
          onPress={() => handleDelete(item.id)}
          style={{
            marginTop: 10,
            backgroundColor: "#ff4d4f",
            paddingVertical: 6,
            borderRadius: 6,
          }}
        >
          <Text style={{ textAlign: "center", color: "#fff" }}>
            {deleting ? "Deleting..." : "Delete"}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <ScrollView style={{ flex: 1, padding: 16 }}>
      <Text style={{ fontSize: 22, fontWeight: "700", marginBottom: 10 }}>
        Thumbnail Manager
      </Text>

      {/* Filter section */}
      <View style={{ marginBottom: 15 }}>
        <Text style={{ fontWeight: "600", marginBottom: 5 }}>Filters</Text>
        {["categoryId", "collectionId", "productMediaId", "userId"].map((f) => (
          <TextInput
            key={f}
            placeholder={`Filter by ${f}`}
            value={filters[f]}
            onChangeText={(t) => handleFilterChange(f, t)}
            style={{
              borderWidth: 1,
              borderColor: "#ddd",
              borderRadius: 8,
              padding: 10,
              marginBottom: 8,
            }}
          />
        ))}

        <TouchableOpacity
          onPress={applyFilters}
          style={{
            backgroundColor: "#007bff",
            padding: 12,
            borderRadius: 8,
          }}
        >
          <Text style={{ color: "#fff", textAlign: "center" }}>Apply Filters</Text>
        </TouchableOpacity>
      </View>

      {/* Upload Form */}
      <TouchableOpacity
        onPress={handlePickImage}
        style={{
          backgroundColor: "#eee",
          padding: 14,
          borderRadius: 8,
          alignItems: "center",
          marginBottom: 10,
        }}
      >
        <Text>{image ? "Change Image" : "Select Image"}</Text>
      </TouchableOpacity>

      {image && (
        <Image
          source={{ uri: image.uri }}
          style={{
            width: "100%",
            height: 180,
            borderRadius: 10,
            marginBottom: 10,
          }}
        />
      )}

      {["size", "format", "category", "collection", "productMedia", "user"].map(
        (field) => (
          <TextInput
            key={field}
            placeholder={field}
            value={formData[field]}
            onChangeText={(text) => handleChange(field, text)}
            style={{
              borderWidth: 1,
              borderColor: "#ddd",
              borderRadius: 8,
              padding: 10,
              marginBottom: 10,
            }}
          />
        )
      )}

      <TouchableOpacity
        onPress={handleSubmit}
        disabled={creating}
        style={{
          backgroundColor: creating ? "#ccc" : "#28a745",
          padding: 14,
          borderRadius: 8,
          marginBottom: 20,
        }}
      >
        <Text style={{ color: "#fff", textAlign: "center", fontWeight: "600" }}>
          {creating ? "Uploading..." : "Create Thumbnail"}
        </Text>
      </TouchableOpacity>

      {/* Thumbnails List */}
      <Text style={{ fontSize: 18, fontWeight: "600", marginBottom: 10 }}>
        Thumbnails
      </Text>

      {loading ? (
        <ActivityIndicator size="large" color="#007bff" />
      ) : (
        <FlatList
          data={data?.thumbnails || []}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          scrollEnabled={false}
        />
      )}
    </ScrollView>
  );
}
