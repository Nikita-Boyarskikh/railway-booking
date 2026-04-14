import type { Car, Seat } from '@shared/api/schemas';
import CarPanel from '@entities/seat/ui/CarPanel';

interface Props {
  cars: Car[];
  openCars: Set<number>;
  onToggleCar: (carNumber: number) => void;
  selected: Set<string>;
  onToggleSeat: (carNumber: number, seat: Seat) => void;
}

export default function SeatsList({
  cars, openCars, onToggleCar, selected, onToggleSeat,
}: Props) {
  return (
    <div className="space-y-3">
      {cars.map((car) => (
        <CarPanel
          key={car.number}
          car={car}
          isOpen={openCars.has(car.number)}
          onToggle={onToggleCar}
          selected={selected}
          onToggleSeat={onToggleSeat}
        />
      ))}
    </div>
  );
}
