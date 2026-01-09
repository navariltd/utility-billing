/** @type {import('tailwindcss').Config} */
export default {
	content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
	theme: {
		extend: {
			colors: {
				brand: {
					50: "#ecf3ff",
					100: "#dde9ff",
					200: "#c2d6ff",
					300: "#9cb9ff",
					400: "#7592ff",
					500: "#465fff",
					600: "#3641f5",
					700: "#2a31d8",
					800: "#252dae",
					900: "#262e89",
				},
			},
		},
	},
	darkMode: "class",
	plugins: [import("tailwindcss-animate")],
	corePlugins: {
		preflight: false,
	},
};
