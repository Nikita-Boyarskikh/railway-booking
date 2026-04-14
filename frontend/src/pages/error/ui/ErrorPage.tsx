export interface ErrorPageProps {
  header: string;
  message: string;
}

export default function ErrorPage({header, message}: ErrorPageProps) {
  return (
    <div className="text-center py-16">
      <h1 className="text-3xl font-bold text-red-600 mb-2">{header}</h1>
      <p className="text-gray-600">{message}</p>
    </div>
  );
}
