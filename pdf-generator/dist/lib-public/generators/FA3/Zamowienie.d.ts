import { Content } from 'pdfmake/interfaces';
import { Zamowienie } from '../../types/fa3.types';
import { ZamowienieKorekta } from '../../enums/invoice.enums';
export declare function generateZamowienie(orderData: Zamowienie | undefined, zamowienieKorekta: ZamowienieKorekta, p_15: string, rodzajFaktury: string, KodWaluty: string, P_PMarzy?: string): Content[];
