import { TCreatedPdf } from 'pdfmake/build/pdfmake';
import { AdditionalDataTypes } from './types/common.types';
import { Faktura } from './types/fa2.types';
export declare function generateFA2(invoice: Faktura, additionalData: AdditionalDataTypes): TCreatedPdf;
