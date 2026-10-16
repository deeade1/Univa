import { apolloClient } from "../index";

import {
  SIGN_IN_MUTATION,
  CREATE_USER_MUTATION,
  SEND_PASSWORD_RESET_MUTATION,
} from "../../graphql/accounts/auth";

import {
  CONFIRM_EMAIL_MUTATION,
} from "../../graphql/accounts/user";

import { tokenStorage } from "./tokenStorage";
import type { AuthUser } from "../../contexts/AuthContext";
import { setAuthStatus } from "./authState";

// -----------------------------------------------------------------------------
// Sign in
// -----------------------------------------------------------------------------

export type SignInInput = {
  contact: string;
  password: string;
  rememberMe?: boolean;
};

type SignInMutationData = {
  signIn: {
    token: string | null;
    refreshToken: string | null;
    user: AuthUser | null;
  } | null;
};

type SignInMutationVariables = {
  input: {
    contact: string;
    password: string;
    rememberMe: boolean;
  };
};

export async function signIn(
  input: SignInInput,
): Promise<AuthUser> {
  const { data } = await apolloClient.mutate<
    SignInMutationData,
    SignInMutationVariables
  >({
    mutation: SIGN_IN_MUTATION,
    variables: {
      input: {
        contact: input.contact.trim(),
        password: input.password,
        rememberMe: input.rememberMe ?? false,
      },
    },
    fetchPolicy: "no-cache",
  });

  const result = data?.signIn;

  if (!result?.token || !result.refreshToken || !result.user) {
    throw new Error(
      "Sign-in did not return the required authentication data.",
    );
  }

  await tokenStorage.setAccessToken(result.token);
  await tokenStorage.setRefreshToken(result.refreshToken);
  await tokenStorage.setUserData(JSON.stringify(result.user));

  setAuthStatus("authenticated");

  return result.user;
}

// -----------------------------------------------------------------------------
// Registration
// -----------------------------------------------------------------------------

export type CreateUserInput = {
  contact: string;
  password: string;
  sendVerification?: boolean;
};

type CreateUserResult = {
  user: AuthUser | null;
  token: string | null;
  refreshToken: string | null;
  verificationSent: boolean;
};

type CreateUserMutationData = {
  createUser: CreateUserResult | null;
};

type CreateUserMutationVariables = {
  input: {
    contact: string;
    password: string;
    sendVerification: boolean;
  };
};

export async function createUser(
  input: CreateUserInput,
): Promise<{
  user: AuthUser | null;
  verificationSent: boolean;
}> {
  const { data } = await apolloClient.mutate<
    CreateUserMutationData,
    CreateUserMutationVariables
  >({
    mutation: CREATE_USER_MUTATION,
    variables: {
      input: {
        contact: input.contact.trim(),
        password: input.password,
        sendVerification: input.sendVerification ?? true,
      },
    },
    fetchPolicy: "no-cache",
  });

  const result = data?.createUser;

  if (!result) {
    throw new Error("Registration did not return a result.");
  }

  // Email verification is pending: do not establish a local session.
  if (result.verificationSent) {
    return {
      user: result.user,
      verificationSent: true,
    };
  }

  // Without pending verification, require a complete session.
  if (!result.user || !result.token || !result.refreshToken) {
    throw new Error(
      "Registration did not return the required authentication data.",
    );
  }

  await tokenStorage.setAccessToken(result.token);
  await tokenStorage.setRefreshToken(result.refreshToken);
  await tokenStorage.setUserData(JSON.stringify(result.user));

  setAuthStatus("authenticated");

  return {
    user: result.user,
    verificationSent: false,
  };
}

// -----------------------------------------------------------------------------
// Email verification
// -----------------------------------------------------------------------------

type ConfirmEmailMutationData = {
  confirmEmail: {
    success: boolean;
    message: string | null;
    clientMutationId: string | null;
  } | null;
};

type ConfirmEmailMutationVariables = {
  input: {
    token: string;
  };
};

export async function confirmEmail(
  token: string,
): Promise<{
  success: boolean;
  message: string;
}> {
  const normalizedToken = token.trim();

  if (!normalizedToken) {
    throw new Error("Verification token is required.");
  }

  const { data } = await apolloClient.mutate<
    ConfirmEmailMutationData,
    ConfirmEmailMutationVariables
  >({
    mutation: CONFIRM_EMAIL_MUTATION,
    variables: {
      input: {
        token: normalizedToken,
      },
    },
    fetchPolicy: "no-cache",
  });

  const result = data?.confirmEmail;

  if (!result) {
    throw new Error("Email verification returned no result.");
  }

  if (!result.success) {
    throw new Error(
      result.message || "Unable to verify your email address.",
    );
  }

  return {
    success: true,
    message: result.message || "Email verified successfully.",
  };
}

// -----------------------------------------------------------------------------
// Password reset
// -----------------------------------------------------------------------------

export type ForgotPasswordInput = {
  contact: string;
};

type SendPasswordResetMutationData = {
  sendPasswordReset: {
    success: boolean;
  } | null;
};

type SendPasswordResetMutationVariables = {
  input: ForgotPasswordInput;
};

export async function forgotPassword(
  input: ForgotPasswordInput,
): Promise<{ success: boolean }> {
  const { data } = await apolloClient.mutate<
    SendPasswordResetMutationData,
    SendPasswordResetMutationVariables
  >({
    mutation: SEND_PASSWORD_RESET_MUTATION,
    variables: {
      input: {
        contact: input.contact.trim(),
      },
    },
    fetchPolicy: "no-cache",
  });

  const result = data?.sendPasswordReset;

  if (!result) {
    throw new Error("The password-reset request returned no result.");
  }

  return result;
}