import { z } from 'zod';

export const StationSchema = z.object({
  name: z.string(),
  code: z.string(),
});
export type Station = z.infer<typeof StationSchema>;

export const DepartureSchema = z.object({
  uuid: z.string(),
  train_number: z.string(),
  train_name: z.string(),
  departure_time: z.string().nullable(),
  arrival_time: z.string().nullable(),
});
export type Departure = z.infer<typeof DepartureSchema>;

export const DepartureSummarySchema = DepartureSchema.extend({
  free_seat_count: z.number().int().nonnegative(),
  min_price: z.string().nullable(),
});
export type DepartureSummary = z.infer<typeof DepartureSummarySchema>;

export const SeatSchema = z.object({
  number: z.number().int(),
  seat_type: z.string(),
  status: z.enum(['free', 'occupied']),
  price: z.string(),
});
export type Seat = z.infer<typeof SeatSchema>;

export const CarSchema = z.object({
  number: z.number().int(),
  car_type: z.string(),
  features: z.record(z.string(), z.unknown()),
  seats: z.array(SeatSchema),
});
export type Car = z.infer<typeof CarSchema>;

export const SeatsResponseSchema = z.object({
  cars: z.array(CarSchema),
});
export type SeatsResponse = z.infer<typeof SeatsResponseSchema>;

export const PassengerSchema = z.object({
  name: z.string().min(1).max(255),
  passport_number: z.string().min(4).max(64).regex(/^[A-Za-z0-9 -]+$/),
  gender: z.enum(['male', 'female']),
  birth_date: z.string(),
});
export type Passenger = z.infer<typeof PassengerSchema>;

export const OrderItemSchema = z.object({
  car_number: z.number().int().positive(),
  seat_number: z.number().int().positive(),
  passenger: PassengerSchema,
});
export type OrderItem = z.infer<typeof OrderItemSchema>;

export const OrderRequestSchema = z.object({
  departure_uuid: z.string(),
  station_from_code: z.string(),
  station_to_code: z.string(),
  items: z.array(OrderItemSchema).min(1),
  expected_total_price: z.string(),
});
export type OrderRequest = z.infer<typeof OrderRequestSchema>;

export const BookingResponseSchema = z.object({
  departure_uuid: z.string(),
  car_number: z.number().int(),
  seat_number: z.number().int(),
  station_from_code: z.string(),
  station_to_code: z.string(),
  passenger: PassengerSchema,
});
export type BookingResponse = z.infer<typeof BookingResponseSchema>;

export const OrderResponseSchema = z.object({
  uuid: z.string(),
  created_at: z.string(),
  total_price: z.string(),
  total_price_currency: z.string(),
  features: z.record(z.string(), z.unknown()),
  bookings: z.array(BookingResponseSchema),
});
export type OrderResponse = z.infer<typeof OrderResponseSchema>;
