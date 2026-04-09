export interface Station {
  id: number;
  name: string;
  code: string;
}

export interface DepartureSummary {
  departure_id: number;
  train_number: string;
  train_name: string;
  departure_time: string | null;
  arrival_time: string | null;
  free_seat_count: number;
  min_price: string | null;
}

export interface Seat {
  id: number;
  number: number;
  seat_type: string;
  status: 'free' | 'occupied';
  price: string;
}

export interface Car {
  id: number;
  number: number;
  car_type: string;
  features: Record<string, unknown>;
  seats: Seat[];
}

export interface SeatsResponse {
  cars: Car[];
}

export interface OrderItem {
  seat_id: number;
  passenger_name: string;
  passenger_passport: string;
  passenger_gender: 'male' | 'female';
  passenger_birth_date: string;
}

export interface OrderRequest {
  departure_id: number;
  station_from_id: number;
  station_to_id: number;
  items: OrderItem[];
}

export interface BookingResponse {
  id: number;
  departure: number;
  seat: number;
  station_from: number;
  station_to: number;
  passenger: {
    id: number;
    name: string;
    passport_number: string;
    gender: string;
    birth_date: string;
  };
}

export interface OrderResponse {
  id: number;
  created_at: string;
  total_price: string;
  features: Record<string, unknown>;
  bookings: BookingResponse[];
}
