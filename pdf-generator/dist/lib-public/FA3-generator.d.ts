import { TCreatedPdf } from 'pdfmake/build/pdfmake';
import { Faktura } from './types/fa3.types';
import { AdditionalDataTypes } from './types/common.types';
export declare function generateFA3(invoice: Faktura, additionalData: AdditionalDataTypes): TCreatedPdf;
