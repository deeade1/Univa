import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ mode }) => {
  // Load only from apps/frontend/.env
  const env = loadEnv(mode, path.resolve(__dirname), '');

  return {
    plugins: [react()],

    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
        '@scss': path.resolve(__dirname, 'src/assets/scss'),
      },
    },

    server: {
      port: 3000,
      host: '0.0.0.0',
      cors: true,
      proxy: {
        '/graphql': {
          target: 'http://localhost:8001',
          changeOrigin: true,
          secure: false,
        },
      },
    },

    css: {
      preprocessorOptions: {
        scss: {
          includePaths: ['node_modules'],
          additionalData: ``,
        },
      },
    },

    define: {
      __APP_ENV__: JSON.stringify(env.APP_ENV),
      ...Object.keys(env).reduce((acc, key) => {
        // Skip invalid JS identifiers (e.g. Windows vars like "ProgramFiles(x86)")
        if (!/^[A-Za-z_$][A-Za-z0-9_$]*$/.test(key)) return acc;
        acc[`process.env.${key}`] = JSON.stringify(env[key]);
        return acc;
      }, {}),
    },

    envPrefix: 'VITE_',

    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        '@apollo/client',
        'graphql',
        'apollo-upload-client',
        'jquery',
        'bootstrap',
      ],
      esbuildOptions: {
        target: 'es2020',
        supported: {
          'top-level-await': true,
        },
      },
    },

    build: {
      target: 'es2020',
      commonjsOptions: {
        transformMixedEsModules: true,
        include: [/node_modules/, /jquery/, /bootstrap/],
      },
    },
  };
});