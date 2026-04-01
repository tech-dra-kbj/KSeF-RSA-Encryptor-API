import { Content } from 'pdfmake/interfaces';
import { Rozliczenie as Rozliczenie1 } from '../../types/fa1.types';
import { Rozliczenie as Rozliczenie2, Rozliczenie as Rozliczenie3 } from '../../types/fa2.types';
import { Rozliczenie as RozliczenieRR } from '../../types/FaRR.types';
export declare function generateRozliczenie(rozliczenie: Rozliczenie1 | Rozliczenie2 | Rozliczenie3 | RozliczenieRR | undefined, KodWaluty: string): Content[];
