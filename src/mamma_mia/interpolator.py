# Copyright 2025 National Oceanography Centre
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import overload

import numpy as np
import xarray as xr
from loguru import logger
from scipy.spatial import cKDTree


def interpolate(
    interpolators: dict,
    coords: dict,
) -> dict:
    """
    Interpolate geophysical fields at the given coordinates.

    Parameters
    ----------
    interpolators : dict
        Mapping of field names to interpolator objects, where each interpolator
        accepts spatial and temporal coordinates and returns sampled values.
    coords : dict
        Sampling coordinates at which to evaluate each interpolator. Values may
        be single floats or datetime strings, lists of floats or datetime
        strings, or NumPy arrays of ``float64`` or ``datetime64[ns]``.
        Expected keys:

        .. code-block:: python

            {
                "latitude":  [26.834],
                "longitude": [-15.142],
                "depth":     [25.0],
                "time":      ["2023-03-03T00:00:00"],
            }

    Returns
    -------
    dict
        Mapping of field names to interpolated values, with one output entry
        per interpolator keyed by the same name.
    """
    dtypes = {"time": "datetime64[ns]"}
    # convert input values into numpy arrays if they aren't already
    numpy_point = {
        k: np.atleast_1d(np.asarray(v, dtype=dtypes.get(k))) for k, v in coords.items()
    }
    # 2. Run through the KD-tree interpolators
    interpolated_data = {
        key: interp(numpy_point) for key, interp in interpolators.items()
    }

    return interpolated_data


@overload
def create_interpolator(mission: xr.DataTree) -> dict: ...


@overload
def create_interpolator(mission: list[xr.DataTree]) -> list[dict]: ...


@overload
def create_interpolator(mission: dict) -> dict: ...


def create_interpolator(mission: xr.DataTree | list[xr.DataTree] | dict) -> dict | list[dict]:
    if isinstance(mission, dict):
        return _create_interpolator(stores=mission)
    elif isinstance(mission, list):
        return [_create_interpolator(mission=m) for m in mission]
    else:
        return _create_interpolator(mission=mission)



def _haversine_km(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance between two points on the Earth (in km)."""
    R = 6371.0  # Earth radius in km
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


class ProfileKDTreeInterpolator:
    """
    A interpolator that indexes 1D vertical profile columns in a KD-tree (time, lat, lon),
    using 1D linear interpolation vertically and IDW across neighboring profiles horizontally.
    """
    def __init__(
        self, 
        ds: xr.DataArray, 
        variable_name: str, 
        max_horizontal_km: float = 12.5, 
        k_neighbors: int = 12,
        valid_profiles: float = 4
    ):
        self.max_horizontal_km = max_horizontal_km
        self.k_neighbors = k_neighbors
        self.valid_profiles = valid_profiles
        
        da = ds if isinstance(ds, xr.DataArray) else ds[variable_name]
        
        # 1. Identify coordinate and dimension names flexibly
        time_dim = next((d for d in ["time", "time_counter"] if d in da.dims), None)
        depth_dim = next((d for d in ["depth", "deptht", "depthu", "depthv", "depthw"] if d in da.dims or d in da.coords), None)
        
        if depth_dim is None:
            raise ValueError(f"No recognized depth dimension found in variable '{variable_name}'. Got dims: {list(da.dims)}")
            
        self.depth_levels = da.coords[depth_dim].values.astype(np.float64).flatten()
        
        # 2. Identify spatial dimensions (everything except time and depth)
        spatial_dims = [d for d in da.dims if d not in [time_dim, depth_dim] and d is not None]
        
        # 3. Stack spatial dimensions on the DataArray into a single 'spatial_pt' dimension
        da_stacked = da.stack(spatial_pt=spatial_dims) if spatial_dims else da
        
        # 4. Transpose to a uniform layout
        transpose_order = ([time_dim] if time_dim and time_dim in da_stacked.dims else []) + [depth_dim, "spatial_pt"]
        da_final = da_stacked.transpose(*[d for d in transpose_order if d in da_stacked.dims])
        
        # 5. Extract flat latitude and longitude coordinates robustly
        if "nav_lat" in da.coords and "nav_lon" in da.coords:
            lat_arr = da.coords["nav_lat"].values
            lon_arr = da.coords["nav_lon"].values
        else:
            lat_d = next((d for d in ["lat", "latitude"] if d in da.coords), None)
            lon_d = next((d for d in ["lon", "longitude"] if d in da.coords), None)
            if lat_d and lon_d:
                lat_arr = da.coords[lat_d].values
                lon_arr = da.coords[lon_d].values
            else:
                raise ValueError("Could not find recognized latitude and longitude coordinates.")

        if lat_arr.ndim == 1 and lon_arr.ndim == 1:
            lat_grid, lon_grid = np.meshgrid(lat_arr, lon_arr, indexing='ij')
            lat_flat = lat_grid.flatten()
            lon_flat = lon_grid.flatten()
        else:
            lat_flat = np.asarray(lat_arr).flatten()
            lon_flat = np.asarray(lon_arr).flatten()

        tree_points = []
        self.profiles = []
        
        # 6. Iterate and collect valid 1D profiles
        if time_dim and time_dim in da_final.dims:
            time_vals = da_final.coords[time_dim].values
            for t_idx, t_val in enumerate(time_vals):
                t_sec = t_val.astype("datetime64[s]").astype(np.float64)
                sub_matrix = da_final.isel({time_dim: t_idx}).values # shape: (depth, spatial_pt)
                
                for pt_idx in range(sub_matrix.shape[1]):
                    prof_vals = np.asarray(sub_matrix[:, pt_idx]).flatten()
                    if len(prof_vals) != len(self.depth_levels) or np.all(np.isnan(prof_vals)):
                        continue
                    tree_points.append([t_sec, lat_flat[pt_idx], lon_flat[pt_idx]])
                    self.profiles.append({
                        "lat": lat_flat[pt_idx],
                        "lon": lon_flat[pt_idx],
                        "values": prof_vals
                    })
        else:
            sub_matrix = da_final.values # shape: (depth, spatial_pt)
            if sub_matrix.ndim == 1:
                sub_matrix = sub_matrix[:, np.newaxis]
                
            for pt_idx in range(sub_matrix.shape[1]):
                prof_vals = np.asarray(sub_matrix[:, pt_idx]).flatten()
                if len(prof_vals) != len(self.depth_levels) or np.all(np.isnan(prof_vals)):
                    continue
                tree_points.append([0.0, lat_flat[pt_idx], lon_flat[pt_idx]])
                self.profiles.append({
                    "lat": lat_flat[pt_idx],
                    "lon": lon_flat[pt_idx],
                    "values": prof_vals
                })
                
        if not tree_points:
            raise ValueError(f"No valid profiles found for variable '{variable_name}'.")
            
        self.tree_points = np.array(tree_points)
        self.profiles = np.array(self.profiles, dtype=object)
        
        logger.info(f"Building profile-based cKDTree with {len(self.tree_points)} columns...")
        self.tree = cKDTree(self.tree_points)

    def interpolate(self, *args, **kwargs) -> np.ndarray:
        if len(args) == 1 and isinstance(args[0], dict):
            coords = args[0]
            time = coords.get("time")
            depth = coords.get("depth")
            lat = coords.get("lat", coords.get("latitude"))
            lon = coords.get("lon", coords.get("longitude"))
        elif len(args) == 4:
            time, depth, lat, lon = args
        elif kwargs:
            time = kwargs.get("time")
            depth = kwargs.get("depth")
            lat = kwargs.get("lat", kwargs.get("latitude"))
            lon = kwargs.get("lon", kwargs.get("longitude"))
        else:
            raise ValueError("Invalid arguments passed to interpolate.")

        t_arr = np.atleast_1d(time)
        if t_arr.dtype.kind == 'M':
            t_query = t_arr.astype("datetime64[s]").astype(np.float64)
        else:
            t_query = t_arr.astype(np.float64)
            
        q_lat = np.atleast_1d(lat)
        q_lon = np.atleast_1d(lon)
        q_depth = np.atleast_1d(depth)
        
        query_tree_pts = np.column_stack((t_query, q_lat, q_lon))
        
        k = min(self.k_neighbors, len(self.tree_points))
        distances, indices = self.tree.query(query_tree_pts, k=k)
        
        if k == 1:
            indices = np.atleast_1d(indices)[:, None]
            distances = np.atleast_1d(distances)[:, None]
            
        batch_size = len(q_depth)
        results = np.empty(batch_size)

        # Trackers for aggregated warning summaries
        depth_out_of_bounds_count = 0
        horizontal_exceeded_count = 0
        max_depth_excess = 0.0
        max_horiz_excess = 0.0
        
        for i in range(batch_size):
            qd = q_depth[i]
            nearest_profs = self.profiles[indices[i]]
            dists = distances[i]
            
            col_interpolated_values = []
            valid_dists = []
            
            for prof, dist in zip(nearest_profs, dists):
                prof_vals = prof["values"]
                valid_mask = ~np.isnan(prof_vals)
                if not np.any(valid_mask):
                    continue
                    
                clean_depths = self.depth_levels[valid_mask]
                clean_vals = prof_vals[valid_mask]
                
                # 1D linear vertical interpolation along the column
                interpolated_val = np.interp(qd, clean_depths, clean_vals, left=np.nan, right=np.nan)
                if not np.isnan(interpolated_val):
                    col_interpolated_values.append(interpolated_val)
                    valid_dists.append(dist)
                    
            if not col_interpolated_values:
                results[i] = np.nan
                continue
                
            col_interpolated_values = np.array(col_interpolated_values)
            valid_dists = np.array(valid_dists)
            
            if len(col_interpolated_values) == 1 or np.any(valid_dists == 0):
                results[i] = col_interpolated_values[0]
            else:
                # Inverse Distance Weighting across neighboring profiles
                weights = 1.0 / (valid_dists + 1e-12) ** 2
                results[i] = np.sum(col_interpolated_values * weights) / np.sum(weights)
                
            # --- Aggregate Check: Depth Bounds across ALL k neighbors ---
            covering_profs = 0
            total_valid_checked = 0
            point_max_excess = 0.0
            
            for prof in nearest_profs:
                prof_vals = prof["values"]
                valid_mask = ~np.isnan(prof_vals)
                if not np.any(valid_mask):
                    continue
                total_valid_checked += 1
                clean_depths = self.depth_levels[valid_mask]
                min_d, max_d = clean_depths[0], clean_depths[-1]
                
                if min_d <= qd <= max_d:
                    covering_profs += 1
                else:
                    excess = max(min_d - qd, qd - max_d)
                    if excess > point_max_excess:
                        point_max_excess = excess

            # Only flag if less than 50% of the valid neighbors cover this depth
            if total_valid_checked < self.valid_profiles:
                depth_out_of_bounds_count += 1
                if point_max_excess > max_depth_excess:
                    max_depth_excess = point_max_excess
            
            # --- Aggregate Check: Horizontal Distance ---
            nearest_prof = nearest_profs[0]
            h_dist_km = _haversine_km(q_lat[i], q_lon[i], nearest_prof["lat"], nearest_prof["lon"])
            if h_dist_km > self.max_horizontal_km:
                horizontal_exceeded_count += 1
                excess_h = h_dist_km - self.max_horizontal_km
                if excess_h > max_horiz_excess:
                    max_horiz_excess = excess_h

        # --- Single Consolidated Warning Log per Batch ---
        if depth_out_of_bounds_count > 0:
            logger.warning(
                f"[KDTree4D] {depth_out_of_bounds_count}/{batch_size} query points exceeded profile depth Max excess: {max_depth_excess:.1f} m "
            )
            
        if horizontal_exceeded_count > 0:
            logger.warning(
                f"[KDTree4D] {horizontal_exceeded_count}/{batch_size} query points exceeded maximum horizontal "
                f"distance threshold ({self.max_horizontal_km} km). Max excess: {max_horiz_excess:.1f} km."
            )
                
        return results if len(results) > 1 else results[0]

    def __call__(self, coords: dict) -> np.ndarray:
        return self.interpolate(coords)

def _create_interpolator(mission: xr.DataTree | None = None, stores: dict | None = None) -> dict:
    """
    Create a KD-tree 4D interpolator covering all downloaded data stores directly from native grids.

    Parameters
    ----------
    mission : xr.DataTree, optional
        A mission DataTree containing store attributes and trajectory information.
    stores : dict, optional
        A dictionary of data stores generated directly by a simulator integration.

    Returns
    -------
    dictionary containing KD-tree interpolators
    """
    if stores is None:
        stores = {}
    if mission is not None:
        logger.info(f"creating interpolator for mission {mission.attrs['name']}")
    else:
        logger.info("creating interpolator")
        
    if not stores:
        if mission is None:
            raise ValueError("Either mission or stores must be provided")
        stores = mission.attrs["stores"]
        
    interpolator = {}
    for store_key, store in stores.items():
        if store["store"].endswith(".nc"):
            ds = xr.open_dataset(store["store"])
        elif store["store"].endswith(".zarr"):
            ds = xr.open_zarr(store=store["store"])
        else:
            raise ValueError(f"unknown store {store['store']}")
            
        # Standardize dimension names (depth and time variants)
        depth_variants = ["deptht", "depthu", "depthv", "depthw", "depth"]
        depth_dim = next((d for d in depth_variants if d in ds.dims), None)
        
        time_variants = ["time_counter", "time"]
        time_dim = next((d for d in time_variants if d in ds.dims), None)

        rename_dict = {}
        if depth_dim and depth_dim != "depth":
            rename_dict[depth_dim] = "depth"
        if time_dim and time_dim != "time":
            rename_dict[time_dim] = "time"
            
        if rename_dict:
            ds = ds.rename(rename_dict)
            
        if "time" in ds.dims or "time" in ds.coords:
            ds["time"] = ds["time"].astype("datetime64[ns]")

        # Instantiate the KDTree4DInterpolator directly on the native dataset
        interpolator[store_key] = ProfileKDTreeInterpolator(ds, store["variable_name"])
        
    logger.success("KD-tree interpolator created successfully")
    return interpolator
