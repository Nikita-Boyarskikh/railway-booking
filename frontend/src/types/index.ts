export interface Station {
  name: string;
  code: string;
}

export interface DepartureSummary {
  uuid: string;
  train_number: string;
  train_name: string;
  departure_time: string | null;
  arrival_time: string | null;
  free_seat_count: number;
  min_price: string | null;
}

export interface Seat {
  number: number;
  seat_type: string;
  status: 'free' | 'occupied';
  price: string;
}

export interface Car {
  number: number;
  car_type: string;
  features: Record<string, unknown>;
  seats: Seat[];
}

export interface SeatsResponse {
  cars: Car[];
}

export interface OrderItem {
  car_number: number;
  seat_number: number;
  passenger_name: string;
  passenger_passport: string;
  passenger_gender: 'male' | 'female';
  passenger_birth_date: string;
}

export interface OrderRequest {
  departure_uuid: string;
  station_from_code: string;
  station_to_code: string;
  items: OrderItem[];
}

export interface BookingResponse {
  departure_uuid: string;
  car_number: number;
  seat_number: number;
  station_from_code: string;
  station_to_code: string;
  passenger: {
    name: string;
    passport_number: string;
    gender: string;
    birth_date: string;
  };
}

export interface OrderResponse {
  uuid: string;
  created_at: string;
  total_price: string;
  features: Record<string, unknown>;
  bookings: BookingResponse[];
}