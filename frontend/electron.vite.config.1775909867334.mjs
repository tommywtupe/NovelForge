// electron.vite.config.ts
import { resolve } from "path";
import { defineConfig, externalizeDepsPlugin } from "electron-vite";
import vue from "@vitejs/plugin-vue";
import { readFileSync } from "fs";
var __electron_vite_injected_dirname = "D:\\project\\NovelForge\\frontend";
var packageJson = JSON.parse(readFileSync(resolve(__electron_vite_injected_dirname, "package.json"), "utf-8"));
var version = packageJson.version;
var electron_vite_config_default = defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()]
  },
  preload: {
    plugins: [externalizeDepsPlugin()]
  },
  renderer: {
    define: {
      "import.meta.env.VITE_APP_VERSION": JSON.stringify(version)
    },
    resolve: {
      alias: {
        "@renderer": resolve("src/renderer/src"),
        "@": resolve("src/renderer/src")
      }
    },
    plugins: [
      vue(),
      // 添加一个插件来修改CSP
      {
        name: "configure-response-headers",
        configureServer: (server) => {
          server.middlewares.use((_req, res, next) => {
            res.setHeader("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; connect-src 'self' http://127.0.0.1:54321 https://api.github.com; style-src 'self' 'unsafe-inline';");
            next();
          });
        }
      }
    ]
  }
});
export {
  electron_vite_config_default as default
};
