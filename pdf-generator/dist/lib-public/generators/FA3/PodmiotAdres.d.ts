import { Content, Margins } from 'pdfmake/interfaces';
import { Adres } from '../../types/fa3.types';
export declare function generatePodmiotAdres(podmiotAdres: Adres | undefined, headerTitle?: string, isSubheader?: boolean, headerMargin?: Margins): Content[];
