import { Watermark } from 'pdfmake/interfaces';
export declare function generateWatermark(watermark?: string | Watermark): Record<'watermark', Watermark> | null;
