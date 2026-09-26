export type VehicleSearchItem = {
  id: string;
  brand: string;
  model: string;
  variant?: string | null;
  city: string;
  fuel?: string | null;
  transmission?: string | null;
  seats?: number | null;
};

export type PricingPackage = {
  id: string;
  operator_id: string;
  name: string;
  service_type: string;
  duration_minutes: number;
  included_km: string;
  base_price: string;
  tax_rate: string;
  deposit: string;
  currency: string;
  active: boolean;
};

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function searchVehicles(params: {
  city: string;
  pickupAt: string;
  returnAt: string;
}): Promise<VehicleSearchItem[]> {
  const query = new URLSearchParams({
    city: params.city,
    pickup_at: params.pickupAt,
    return_at: params.returnAt
  });
  const response = await fetch(
    `${API_URL}/vehicles/search?${query.toString()}`,
    { cache: "no-store" }
  );
  if (!response.ok) {
    throw new Error(
      "Could not search vehicles. Please review the dates and try again."
    );
  }
  return response.json();
}

export async function getVehiclePackages(
  vehicleId: string,
  serviceType: string
): Promise<PricingPackage[]> {
  const response = await fetch(`${API_URL}/vehicles/${vehicleId}/packages?service_type=${encodeURIComponent(serviceType)}`, {
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error("Rental packages are not available for this vehicle.");
  }
  return response.json();
}
