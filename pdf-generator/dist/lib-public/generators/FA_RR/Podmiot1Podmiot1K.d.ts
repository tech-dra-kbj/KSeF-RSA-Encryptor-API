import { Content } from 'pdfmake/interfaces';
import { Podmiot1Class, Podmiot1KClass } from '../../types/FaRR.types';
export declare function generatePodmiot1Podmiot1K(podmiot1: Podmiot1Class, podmiot1K: Podmiot1KClass): Content[];
export declare function generateCorrectedContent(podmiot: Podmiot1Class | Podmiot1KClass, header: string): Content[];
