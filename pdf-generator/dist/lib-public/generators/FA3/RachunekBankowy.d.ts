import { Content } from 'pdfmake/interfaces';
import { RachunekBankowy } from '../../types/fa3.types';
export declare const generujRachunekBankowy: (accounts?: RachunekBankowy[], title?: string) => Content[];
