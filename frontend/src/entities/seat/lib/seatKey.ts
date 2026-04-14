export const seatKey = (carNumber: number, seatNumber: number) => `${carNumber}:${seatNumber}`;

export function parseSeatKey(key: string): { carNumber: number; seatNumber: number } {
  const [carStr = '', seatStr = ''] = key.split(':');
  return { carNumber: Number(carStr), seatNumber: Number(seatStr) };
}
