import { Content } from 'pdfmake/interfaces';
import { FP, Naglowek, Stopka } from '../../types/fa2.types';
import { Zalacznik } from '../../types/fa3.types';
import { AdditionalDataTypes } from '../../types/common.types';
export declare function generateStopka(additionalData?: AdditionalDataTypes, stopka?: Stopka, naglowek?: Naglowek, wz?: FP[], zalacznik?: Zalacznik): Content[];
