import { Content } from 'pdfmake/interfaces';
import { Zalacznik } from '../../types/fa3.types';
export declare function generateZalaczniki(zalacznik?: Zalacznik): Content[];
export declare function chunkArray<T>(columns: T[]): T[][];
