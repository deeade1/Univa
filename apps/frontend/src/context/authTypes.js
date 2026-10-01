// src/context/authTypes.js

/**
 * @typedef {'guest' | 'basic' | 'verified' | 'transaction' | 'real_estate' | 'ride' | 'logistics'} AuthLevel
 * Represents the user's authentication level.
 */

/**
 * @typedef {'general' | 'ecommerce' | 'taxi' | 'logistics' | 'real_estate' | 'banking' | 'social'} ServiceType
 * Represents supported service categories.
 */

/**
 * @typedef {Object} DeviceInfo
 * @property {string} id
 * @property {string} [fingerprint]
 * @property {string} [name]
 * @property {string} [type]
 * @property {string} [os]
 * @property {Date} [lastUsed]
 * @property {string} [ipAddress]
 */

/**
 * @typedef {DeviceInfo & {
 *   deviceType: 'face' | 'fingerprint' | 'voice',
 *   isActive?: boolean
 * }} BiometricDevice
 */

/**
 * @typedef {Object} User
 * @property {string} id
 * @property {string} [email]
 * @property {string} [phoneNumber]
 * @property {AuthLevel} [authLevel]
 * @property {boolean} [verified]
 * @property {DeviceInfo[]} [devices]
 * @property {string[]} [services]
 * @property {string} [firstName]
 * @property {string} [username]
 */

/**
 * @typedef {Object} AuthResponse
 * @property {string} token
 * @property {string} [refreshToken]
 * @property {User} user
 * @property {boolean} [requiresFaceVerification]
 * @property {boolean} [verificationSent]
 * @property {boolean} [requiresVerification]
 * @property {'email' | 'sms' | 'otp' | 'face'} [verificationMethod]
 * @property {AuthLevel} [authLevel]
 * @property {number} [expiresIn]
 */

/**
 * @typedef {Object} AuthEvent
 * @property {'login' | 'logout' | 'upgrade' | 'verification'} type
 * @property {Date} timestamp
 * @property {string} userId
 * @property {string} [service]
 * @property {DeviceInfo} [device]
 * @property {string} [ipAddress]
 * @property {Object<string, any>} [metadata]
 */

/**
 * @typedef {Object} ServiceConfig
 * @property {string} name
 * @property {AuthLevel} authLevel
 * @property {number} [sessionTimeout]
 * @property {boolean} [requiresMFA]
 * @property {number} [allowedDevices]
 */

/**
 * @typedef {User & {
 *   exp: number,
 *   iat: number,
 *   iss: string,
 *   aud: string,
 *   services?: string[],
 *   deviceId?: string,
 *   authLevel: AuthLevel
 * }} JWTClaims
 */

export {};
