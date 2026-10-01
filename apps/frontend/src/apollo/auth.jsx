// src/apollo/auth.js
export const getAccessToken = async () => localStorage.getItem("accessToken");
export const getRefreshToken = async () => localStorage.getItem("refreshToken");

export const setTokens = async (token, refreshToken) => {
  localStorage.setItem("accessToken", token);
  if (refreshToken) localStorage.setItem("refreshToken", refreshToken);
};

export const clearTokens = async () => {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
};
