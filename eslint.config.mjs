// Flat-config ESLint setup for the Electron/TypeScript code.
// Non-type-checked recommended rules to keep CI reliable without a project graph.
// `no-explicit-any` is a warning (not error) so it doesn't block CI on day one.
import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
    {
        // Vendored / build / dependency dirs are never linted.
        ignores: [
            'texthooker/**',
            'GSM_Overlay/**',
            'dist/**',
            'node_modules/**',
            '**/*.d.ts',
        ],
    },
    js.configs.recommended,
    ...tseslint.configs.recommended,
    {
        files: ['electron-src/**/*.{ts,tsx}'],
        languageOptions: {
            ecmaVersion: 'latest',
            sourceType: 'module',
        },
        rules: {
            // Soft-fail on existing `any`s so the lint job is informational on day one.
            '@typescript-eslint/no-explicit-any': 'warn',
            '@typescript-eslint/no-unused-vars': [
                'warn',
                { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
            ],
        },
    }
);
