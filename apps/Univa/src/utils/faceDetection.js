// apps/Univa/utils/faceDetection.js
import * as tf from '@tensorflow/tfjs';
import '@tensorflow/tfjs-react-native';
import * as faceLandmarksDetection from '@tensorflow-models/face-landmarks-detection';

class FaceDetectionService {
  static model = null;
  static isModelLoaded = false;

  static async loadModel() {
    try {
      // Initialize TensorFlow
      await tf.ready();
      console.log('TensorFlow.js is ready');

      // Load face detection model
      this.model = await faceLandmarksDetection.load(
        faceLandmarksDetection.SupportedPackages.mediapipeFacemesh,
        {
          maxFaces: 1,
          refineLandmarks: true,
          flipHorizontal: false,
        }
      );
      
      this.isModelLoaded = true;
      console.log('Face detection model loaded');
      return true;
    } catch (error) {
      console.error('Failed to load face detection model:', error);
      return false;
    }
  }

  static async detectFace(imageUri) {
    if (!this.isModelLoaded || !this.model) {
      const loaded = await this.loadModel();
      if (!loaded) {
        throw new Error('Face detection model not loaded');
      }
    }

    try {
      // Load and preprocess image
      const imageTensor = await this.loadImageTensor(imageUri);
      
      // Detect faces
      const predictions = await this.model.estimateFaces({
        input: imageTensor,
        returnTensors: false,
        flipHorizontal: false,
        predictIrises: false,
      });

      // Clean up tensor
      imageTensor.dispose();

      if (predictions.length > 0) {
        const face = predictions[0];
        return {
          success: true,
          face: {
            boundingBox: face.boundingBox,
            landmarks: face.landmarks,
            probability: face.faceInViewConfidence || 0,
            leftEyeOpenProbability: this.getEyeOpenProbability(face, 'left'),
            rightEyeOpenProbability: this.getEyeOpenProbability(face, 'right'),
            smilingProbability: face.silent?.smilingProbability || 0,
          }
        };
      }

      return { success: false, message: 'No face detected' };
    } catch (error) {
      console.error('Face detection error:', error);
      return { success: false, error: error.message };
    }
  }

  static async loadImageTensor(imageUri) {
    // This is a simplified version - you'll need to implement 
    // image loading based on your platform
    // For React Native, you might use react-native-image-picker or similar
    
    // For now, return a placeholder
    // You'll need to implement actual image loading
    throw new Error('Image loading not implemented. Use expo-image-manipulator to process images first.');
  }

  static getEyeOpenProbability(face, eye) {
    // Simplified eye open probability calculation
    // In a real implementation, you'd analyze landmark points
    return eye === 'left' ? 0.8 : 0.8; // Placeholder values
  }

  static detectBlink(face) {
    if (!face.leftEyeOpenProbability || !face.rightEyeOpenProbability) {
      return false;
    }
    
    // Both eyes closed or mostly closed
    const leftEyeClosed = face.leftEyeOpenProbability < 0.3;
    const rightEyeClosed = face.rightEyeOpenProbability < 0.3;
    
    return leftEyeClosed && rightEyeClosed;
  }
}

export default FaceDetectionService;