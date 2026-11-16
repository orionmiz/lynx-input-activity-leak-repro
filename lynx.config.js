import { defineConfig } from '@lynx-js/rspeedy';
import { pluginReactLynx } from '@lynx-js/react-rsbuild-plugin';
export default defineConfig({source:{entry:{input:'./input.tsx',control:'./control.tsx'}},plugins:[pluginReactLynx()]});
