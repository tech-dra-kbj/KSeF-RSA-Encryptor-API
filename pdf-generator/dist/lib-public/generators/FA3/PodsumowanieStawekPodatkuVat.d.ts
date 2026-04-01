import { Content } from 'pdfmake/interfaces';
import { Fa, Faktura } from '../../types/fa3.types';
import { TaxSummaryTypes } from '../../types/tax-summary.types';
export declare function generatePodsumowanieStawekPodatkuVat(faktura: Faktura): Content[];
export declare function getSummaryTaxRate(fa: Fa): TaxSummaryTypes[];
