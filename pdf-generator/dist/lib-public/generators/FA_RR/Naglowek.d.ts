import { Content } from 'pdfmake/interfaces';
import { FakturaRR as Fa } from '../../types/FaRR.types';
import { AdditionalDataTypes } from '../../types/common.types';
export declare function generateNaglowek(fa?: Fa, additionalData?: AdditionalDataTypes): Content[];
