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

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

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
  const response = await fetch(`${API_URL}/vehicles/search?${query.toString()}`, {
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error("Could not search vehicles. Please review the dates and try again.");
  }
  return response.json();
}
