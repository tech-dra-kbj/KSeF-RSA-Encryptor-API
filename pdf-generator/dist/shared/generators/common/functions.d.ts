import { FP as FP2 } from '../../../lib-public/types/fa2.types';
export declare function translateMap(value: FP2 | string | undefined, map: Record<string, string>): string;
export declare function formatDateTime(data?: string, withoutSeconds?: boolean, withoutTime?: boolean): string;
export declare function getDateTimeWithoutSeconds(isoDate?: FP2): string;
export declare function formatTime(data?: string, withoutSeconds?: boolean): string;
