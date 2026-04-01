import { Content } from 'pdfmake/interfaces';
import { Fa as Fa1 } from '../../types/fa1.types';
import { Fa as Fa2 } from '../../types/fa2.types';
import { Fa as Fa3, Zalacznik } from '../../types/fa3.types';
import { AdditionalDataTypes } from '../../types/common.types';
export declare function generateNaglowek(fa?: Fa2 | Fa3 | Fa1, additionalData?: AdditionalDataTypes, zalacznik?: Zalacznik): Content[];
