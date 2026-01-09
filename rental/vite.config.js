import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig, loadEnv } from "vite";
import svgr from "vite-plugin-svgr";
import proxyOptions from "./proxyOptions.js";

export default defineConfig(({ mode }) => {
	const env = loadEnv(mode, process.cwd(), "");

	return {
		plugins: [react(), svgr()],

		server: {
			port: 8080,
			proxy: proxyOptions,
		},

		resolve: {
			alias: {
				"@": path.resolve(__dirname, "./src"),
			},
		},

		build: {
			outDir: "../utility_billing/public/rental",
			emptyOutDir: true,
			target: "es2015",
		},
	};
});
