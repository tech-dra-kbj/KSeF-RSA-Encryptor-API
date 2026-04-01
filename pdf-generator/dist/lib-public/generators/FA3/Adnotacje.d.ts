import { Content } from 'pdfmake/interfaces';
import { Adnotacje, NoweSrodkiTransportu } from '../../types/fa3.types';
export declare function generateAdnotacje(adnotacje?: Adnotacje): Content[];
export declare function generateDostawy(noweSrodkiTransportu: NoweSrodkiTransportu): Content[];
