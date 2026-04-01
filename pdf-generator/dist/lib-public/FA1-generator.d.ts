import { TCreatedPdf } from 'pdfmake/build/pdfmake';
import { Faktura } from './types/fa1.types';
import { AdditionalDataTypes } from './types/common.types';
export declare function generateFA1(invoice: Faktura, additionalData: AdditionalDataTypes): TCreatedPdf;
