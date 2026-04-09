import { Link, Route, Routes } from 'react-router-dom';
import SearchPage from './pages/SearchPage';
import SeatsPage from './pages/SeatsPage';
import ConfirmationPage from './pages/ConfirmationPage';

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <header className="bg-blue-700 text-white px-6 py-4 shadow">
        <Link to="/" className="text-xl font-semibold">Railway Booking</Link>
      </header>
      <main className="max-w-5xl mx-auto p-6">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/departures/:id/seats" element={<SeatsPage />} />
          <Route path="/orders/:id" element={<ConfirmationPage />} />
        </Routes>
      </main>
    </div>
  );
}
