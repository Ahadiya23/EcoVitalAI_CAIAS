import { Link } from "react-router-dom";

export function DemoBanner({ city }: { city: "delhi" | "bangalore" | "mumbai" }) {
  return (
    <div className="mb-4 rounded-md bg-amber-100 px-4 py-3 text-amber-900">
      <div className="flex items-center justify-between">
        <span className="font-medium">Demo Mode - {city[0].toUpperCase() + city.slice(1)}</span>
        <div className="flex gap-3 text-sm">
          <Link to="/?demo=delhi">Try Delhi</Link>
          <Link to="/?demo=mumbai">Try Mumbai</Link>
          <Link to="/?demo=bangalore">Try Bangalore</Link>
        </div>
      </div>
    </div>
  );
}
