import { Content } from 'pdfmake/interfaces';
import { Podmiot1Class, Podmiot1KClass } from '../../types/FaRR.types';
export declare function generatePodmiot2Podmiot2K(podmiot2: Podmiot1Class, podmiot2K: Podmiot1KClass): Content[];
export declare function generateCorrectedContent(podmiot: Podmiot1Class | Podmiot1KClass, header: string): Content[];
