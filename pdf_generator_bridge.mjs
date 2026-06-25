import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const bridgeDir = path.dirname(fileURLToPath(import.meta.url));

// Redirect console output to stderr so module debug messages don't pollute stdout JSON
const _toStderr = (...args) => process.stderr.write(args.join(' ') + '\n');
console.log = _toStderr;
console.warn = _toStderr;
console.info = _toStderr;
console.debug = _toStderr;

// FileReader is a browser API not available in Node.js — polyfill using File.text()
if (typeof globalThis.FileReader === 'undefined') {
  globalThis.FileReader = class FileReader {
    readAsText(blob) {
      blob.text().then((text) => {
        this.result = text;
        if (typeof this.onload === 'function') {
          this.onload({ target: { result: text } });
        }
      }).catch((err) => {
        if (typeof this.onerror === 'function') this.onerror(err);
      });
    }
  };
}

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }

  return Buffer.concat(chunks).toString('utf-8');
}

function resolveModulePath() {
  if (process.env.KSEF_PDF_MODULE_PATH) {
    return process.env.KSEF_PDF_MODULE_PATH;
  }

  return path.resolve(bridgeDir, 'pdf-generator', 'dist', 'ksef-fe-invoice-converter.js');
}

async function main() {
  const rawInput = await readStdin();
  const payload = JSON.parse(rawInput || '{}');

  const xmlContent = String(payload.xmlContent ?? '');
  const additionalData =
    payload.additionalData && typeof payload.additionalData === 'object' ? payload.additionalData : {};
  const language = typeof payload.language === 'string' ? payload.language.toLowerCase() : 'pl';

  if (!xmlContent.trim()) {
    throw new Error('xmlContent is required');
  }

  const modulePath = resolveModulePath();
  const moduleUrl = pathToFileURL(path.resolve(modulePath)).href;
  const pdfModule = await import(moduleUrl);

  if (typeof pdfModule.generateInvoice !== 'function') {
    throw new Error('generateInvoice export not found in PDF module');
  }

  await pdfModule.i18nReady;
  await pdfModule.i18next.changeLanguage(language);

  const xmlFile = new File([xmlContent], 'invoice.xml', { type: 'text/xml' });
  const base64 = await pdfModule.generateInvoice(xmlFile, additionalData, 'base64');
  process.stdout.write(JSON.stringify({ base64 }));
}

main().catch((error) => {
  const errorMessage = error instanceof Error ? error.message : String(error);
  process.stderr.write(errorMessage);
  process.exit(1);
});
