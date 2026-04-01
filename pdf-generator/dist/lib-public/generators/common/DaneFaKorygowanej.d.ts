import { Content } from 'pdfmake/interfaces';
import { Fa as Fa1 } from '../../types/fa1.types';
import { Fa as Fa2 } from '../../types/fa2.types';
import { Fa as Fa3 } from '../../types/fa3.types';
import { FakturaRR as FaRR } from '../../types/FaRR.types';
export declare function generateDaneFaKorygowanej(invoice?: Fa1 | Fa2 | Fa3 | FaRR): Content[];
