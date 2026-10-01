// apps/Univa/utils/validators.js
export const validateTransfer = (transferData) => {
  if (!transferData.accountNumber || transferData.accountNumber.trim() === '') {
    return 'Account number is required';
  }
  
  if (transferData.accountNumber.length < 10) {
    return 'Account number must be at least 10 digits';
  }
  
  if (!/^\d+$/.test(transferData.accountNumber)) {
    return 'Account number must contain only digits';
  }
  
  if (!transferData.bankCode || transferData.bankCode.trim() === '') {
    return 'Bank code is required';
  }
  
  if (!transferData.amount) {
    return 'Amount is required';
  }
  
  const amount = parseFloat(transferData.amount);
  if (isNaN(amount) || amount <= 0) {
    return 'Please enter a valid amount';
  }
  
  if (amount > 1000000000) { // 1 billion limit
    return 'Amount exceeds maximum transfer limit';
  }
  
  if (!transferData.fromAccountId) {
    return 'Source account is required';
  }
  
  return null;
};

export const validateBankCode = (bankCode) => {
  if (!bankCode || bankCode.trim() === '') {
    return 'Bank code is required';
  }
  
  // You can add specific bank code validation logic here
  // For Nigeria: e.g., "044" for Access Bank, "058" for GTBank, etc.
  const validBankCodes = ['044', '058', '050', '070', '011', '214', '030'];
  
  if (!validBankCodes.includes(bankCode)) {
    return 'Invalid bank code';
  }
  
  return null;
};

export const validateNarration = (narration) => {
  if (narration && narration.length > 100) {
    return 'Narration cannot exceed 100 characters';
  }
  
  return null;
};

export const validatePhoneNumber = (phone) => {
  if (!phone || phone.trim() === '') {
    return 'Phone number is required';
  }
  
  // Basic phone validation - adjust for your country
  const phoneRegex = /^[0-9]{10,15}$/;
  if (!phoneRegex.test(phone.replace(/\D/g, ''))) {
    return 'Please enter a valid phone number';
  }
  
  return null;
};

export const validateEmail = (email) => {
  if (!email || email.trim() === '') {
    return 'Email is required';
  }
  
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    return 'Please enter a valid email address';
  }
  
  return null;
};

export const validatePassword = (password) => {
  if (!password || password.trim() === '') {
    return 'Password is required';
  }
  
  if (password.length < 8) {
    return 'Password must be at least 8 characters';
  }
  
  if (!/[A-Z]/.test(password)) {
    return 'Password must contain at least one uppercase letter';
  }
  
  if (!/[0-9]/.test(password)) {
    return 'Password must contain at least one number';
  }
  
  if (!/[!@#$%^&*]/.test(password)) {
    return 'Password must contain at least one special character (!@#$%^&*)';
  }
  
  return null;
};

export const validateFaceImage = (imageUri) => {
  if (!imageUri || typeof imageUri !== 'string') {
    return 'Invalid image';
  }
  
  // Check if URI has a valid image extension
  const validExtensions = ['.jpg', '.jpeg', '.png', '.webp'];
  const hasValidExtension = validExtensions.some(ext => 
    imageUri.toLowerCase().endsWith(ext)
  );
  
  if (!hasValidExtension) {
    return 'Image must be JPG, PNG, or WebP format';
  }
  
  return null;
};

// Form validation hook for reusable validation logic
export const useFormValidation = () => {
  const validateField = (fieldName, value, rules) => {
    if (rules.required && (!value || value.trim() === '')) {
      return `${fieldName} is required`;
    }
    
    if (rules.minLength && value.length < rules.minLength) {
      return `${fieldName} must be at least ${rules.minLength} characters`;
    }
    
    if (rules.maxLength && value.length > rules.maxLength) {
      return `${fieldName} cannot exceed ${rules.maxLength} characters`;
    }
    
    if (rules.pattern && !rules.pattern.test(value)) {
      return rules.message || `Invalid ${fieldName}`;
    }
    
    if (rules.validate && typeof rules.validate === 'function') {
      const customError = rules.validate(value);
      if (customError) return customError;
    }
    
    return null;
  };
  
  const validateForm = (formData, validationRules) => {
    const errors = {};
    
    Object.keys(validationRules).forEach(fieldName => {
      const value = formData[fieldName];
      const rules = validationRules[fieldName];
      const error = validateField(fieldName, value, rules);
      
      if (error) {
        errors[fieldName] = error;
      }
    });
    
    return {
      isValid: Object.keys(errors).length === 0,
      errors
    };
  };
  
  return {
    validateField,
    validateForm
  };
};