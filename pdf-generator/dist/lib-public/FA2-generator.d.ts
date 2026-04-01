import { TCreatedPdf } from 'pdfmake/build/pdfmake';
import { Faktura } from './types/fa2.types';
import { AdditionalDataTypes } from './types/common.types';
export declare function generateFA2(invoice: Faktura, additionalData: AdditionalDataTypes): TCreatedPdf;
