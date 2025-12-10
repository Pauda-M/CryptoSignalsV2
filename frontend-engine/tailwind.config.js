export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        "pb-dark": "#0c0c0f",
        "pb-blue": "#0ea5e9",
        "pb-cyan": "#22d3ee",
        "pb-gold": "#fcd34d",
      },
      boxShadow: {
        "pb": "0 4px 18px rgba(0,0,0,0.45)"
      },
    },
  },
  plugins: [],
};
