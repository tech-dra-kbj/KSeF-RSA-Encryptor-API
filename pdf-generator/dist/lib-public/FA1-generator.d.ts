import { TCreatedPdf } from 'pdfmake/build/pdfmake';
import { AdditionalDataTypes } from './types/common.types';
import { Faktura } from './types/fa1.types';
export declare function generateFA1(invoice: Faktura, additionalData: AdditionalDataTypes): TCreatedPdf;
