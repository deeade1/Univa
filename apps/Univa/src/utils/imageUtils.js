// apps/Univa/utils/imageUtils.js
import * as FileSystem from 'expo-file-system';
import * as ImageManipulator from 'expo-image-manipulator';
import { decode } from 'base64-arraybuffer';
import * as tf from '@tensorflow/tfjs';

export class ImageUtils {
  static async prepareImageForTensorFlow(imageUri, targetSize = 224) {
    try {
      // 1. Read the image file
      const base64 = await FileSystem.readAsStringAsync(imageUri, {
        encoding: FileSystem.EncodingType.Base64,
      });

      // 2. Convert base64 to array buffer
      const arrayBuffer = decode(base64);
      
      // 3. Create a blob
      const blob = new Blob([arrayBuffer], { type: 'image/jpeg' });
      
      // 4. Create image element (simplified approach)
      // Note: This is a simplified version. In production, you might need
      // to use a different approach for React Native
      
      // For now, we'll use a different approach - resize and process
      return await this.alternativeImageProcessing(imageUri, targetSize);
      
    } catch (error) {
      console.error('Image preparation error:', error);
      throw error;
    }
  }

  static async alternativeImageProcessing(imageUri, targetSize) {
    // Alternative: Use ImageManipulator to resize and get base64
    const resized = await ImageManipulator.manipulateAsync(
      imageUri,
      [{ resize: { width: targetSize, height: targetSize } }],
      { 
        compress: 0.8, 
        format: ImageManipulator.SaveFormat.JPEG,
        base64: true 
      }
    );

    // Create a simple tensor from the resized image
    // This is a simplified approach - in production you'd need
    // proper image decoding
    return resized.base64;
  }

  static async checkImageQuality(imageUri) {
    try {
      const { size } = await FileSystem.getInfoAsync(imageUri);
      
      // Check if image is too small
      if (size < 50000) { // Less than 50KB
        return { 
          quality: 'poor', 
          message: 'Image is too small or low quality' 
        };
      }
      
      return { 
        quality: 'good', 
        message: 'Image quality is acceptable' 
      };
    } catch (error) {
      return { 
        quality: 'unknown', 
        message: 'Could not check image quality' 
      };
    }
  }
}