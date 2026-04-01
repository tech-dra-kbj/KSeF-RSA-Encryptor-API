import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const bridgeDir = path.dirname(fileURLToPath(import.meta.url));

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

  if (!xmlContent.trim()) {
    throw new Error('xmlContent is required');
  }

  const modulePath = resolveModulePath();
  const moduleUrl = pathToFileURL(path.resolve(modulePath)).href;
  const pdfModule = await import(moduleUrl);

  if (typeof pdfModule.generateInvoiceFromXml !== 'function') {
    throw new Error('generateInvoiceFromXml export not found in PDF module');
  }

  const base64 = await pdfModule.generateInvoiceFromXml(xmlContent, additionalData, 'base64');
  process.stdout.write(JSON.stringify({ base64 }));
}

main().catch((error) => {
  const errorMessage = error instanceof Error ? error.message : String(error);
  process.stderr.write(errorMessage);
  process.exit(1);
});
