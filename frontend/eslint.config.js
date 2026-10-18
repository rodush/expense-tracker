import eslint from "@eslint/js";
import prettier from "eslint-config-prettier";
import globals from "globals";
import svelte from "eslint-plugin-svelte";

export default [
  {
    ignores: ["../app/static/frontend/**", "coverage/**", "node_modules/**"],
  },
  eslint.configs.recommended,
  ...svelte.configs.recommended,
  {
    files: ["src/**/*.{js,svelte}", "vite.config.js"],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
  },
  prettier,
];
