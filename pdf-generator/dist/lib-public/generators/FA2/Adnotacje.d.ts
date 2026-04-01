import { Content } from 'pdfmake/interfaces';
import { Adnotacje, NoweSrodkiTransportu } from '../../types/fa2.types';
export declare function generateAdnotacje(adnotacje?: Adnotacje): Content[];
export declare function generateDostawy(noweSrodkiTransportu: NoweSrodkiTransportu): Content[];
