import { TCreatedPdf } from 'pdfmake/build/pdfmake';
import { AdditionalDataTypes } from './types/common.types';
import { FaRR } from './types/FaRR.types';
export declare function generateFARR(invoice: FaRR, additionalData: AdditionalDataTypes): TCreatedPdf;
