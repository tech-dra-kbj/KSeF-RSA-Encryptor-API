import { Content } from 'pdfmake/interfaces';
import { Podmiot2, Podmiot2K } from '../../types/fa1.types';
export declare function generatePodmiot2Podmiot2K(podmiot2: Podmiot2, podmiot2K: Podmiot2K): Content[];
export declare function generateCorrectedContent(podmiot: Podmiot2 | Podmiot2K, headerText: string): Content[];
