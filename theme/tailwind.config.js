/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "../generator/templates/**/*.html",
    "../templates/**/*.html",
    "../generator/**/*.py",
  ],
  darkMode: "class",
  theme: {
    extend: {},
  },
  plugins: [],
};
