import type { CodegenConfig } from "@graphql-codegen/cli";

const config: CodegenConfig = {
  schema: "http://localhost:8000/graphql/", // or from env var
  documents: [
    "apps/frontend/src/queries/**/*.ts",
    "apps/univa-mobile-app/app/queries/**/*.ts",
  ],
  generates: {
    // ✅ Put generated types in shared folder
    "apps/shared/types/graphql.ts": {
      plugins: [
        "typescript",
        "typescript-operations",
        "typescript-react-apollo",
      ],
      config: {
        withHooks: true,
      },
    },
  },
  ignoreNoDocuments: true,
};

export default config;
