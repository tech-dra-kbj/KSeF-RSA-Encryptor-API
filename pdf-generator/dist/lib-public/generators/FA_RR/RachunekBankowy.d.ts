import { Content } from 'pdfmake/interfaces';
import { RachunekBankowy } from '../../types/FaRR.types';
export declare const generujRachunekBankowy: (accounts?: RachunekBankowy[], title?: string) => Content[];
