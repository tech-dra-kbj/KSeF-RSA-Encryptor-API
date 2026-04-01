import { Content } from 'pdfmake/interfaces';
import { Podmiot1, Podmiot1K } from '../../types/fa1.types';
export declare function generatePodmiot1Podmiot1K(podmiot1: Podmiot1, podmiot1K: Podmiot1K): Content[];
export declare function generateCorrectedContent(podmiot: Podmiot1 | Podmiot1K, headerText: string): Content[];
