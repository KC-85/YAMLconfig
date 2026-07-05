import { copyFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const themeRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const assets = [
  ["node_modules/alpinejs/dist/cdn.min.js", "static/vendor/alpinejs/alpine.min.js"],
  ["node_modules/codemirror/lib/codemirror.css", "static/vendor/codemirror/codemirror.css"],
  ["node_modules/codemirror/lib/codemirror.js", "static/vendor/codemirror/codemirror.js"],
  ["node_modules/codemirror/mode/yaml/yaml.js", "static/vendor/codemirror/yaml.js"],
];

for (const [source, destination] of assets) {
  const outputPath = resolve(themeRoot, destination);
  await mkdir(dirname(outputPath), { recursive: true });
  await copyFile(resolve(themeRoot, source), outputPath);
}
