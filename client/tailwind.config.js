/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                dark: {
                    900: '#1a1b1e',
                    800: '#25262b',
                    700: '#2c2e33',
                },
                brand: {
                    500: '#3b5bdb',
                },
                danger: {
                    500: '#fa5252',
                    900: '#c92a2a'
                },
                safe: {
                    500: '#40c057',
                }
            }
        },
    },
    plugins: [],
}
