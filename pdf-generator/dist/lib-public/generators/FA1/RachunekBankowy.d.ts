import { Content } from 'pdfmake/interfaces';
import { FP } from '../../types/fa1.types';
export declare const generujRachunekBankowy: (accounts?: Record<string, FP>[], title?: string) => Content[];
