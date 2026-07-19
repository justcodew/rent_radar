import type { Listing } from "./index";

export interface SubwayStation {
  name: string;
  lat: number;
  lng: number;
  lines: string[];
}

export interface CommunityInfo {
  name: string;
  lat: number;
  lng: number;
  distance_km: number;
  bearing_deg: number;
  listings_count?: number;
  sample_listings?: Listing[];
}

export interface SubwayExploreResult {
  station: SubwayStation;
  radius_km: number;
  communities: CommunityInfo[]; // 按 distance_km 升序
}
