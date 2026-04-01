import { AdditionalDataTypes } from './types/common.types';
export declare function generateInvoiceFromXml(xmlContent: string, additionalData: AdditionalDataTypes, formatType: 'uint8array'): Promise<Uint8Array>;
export declare function generateInvoiceFromXml(xmlContent: string, additionalData: AdditionalDataTypes, formatType: 'base64'): Promise<string>;
