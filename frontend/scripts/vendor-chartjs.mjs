import { copyFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const frontendDirectory = resolve(scriptDirectory, '..');
const repositoryDirectory = resolve(frontendDirectory, '..');
const vendorDirectory = resolve(repositoryDirectory, 'app/static/vendor');

await mkdir(vendorDirectory, { recursive: true });
await copyFile(
  resolve(frontendDirectory, 'node_modules/chart.js/dist/chart.umd.min.js'),
  resolve(vendorDirectory, 'chart.umd.min.js'),
);
await copyFile(
  resolve(frontendDirectory, 'node_modules/chart.js/LICENSE.md'),
  resolve(vendorDirectory, 'CHARTJS-LICENSE.md'),
);
