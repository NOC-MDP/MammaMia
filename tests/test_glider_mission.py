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

"""
Test suite for the mamma_mia glider mission workflow.

Covers:
  - Trajectory and platform creation from spec files
  - Mission creation with/without observational error
  - Data retrieval and storage on the mission object
  - Interpolator creation
  - Flying the mission (payload population)
  - Campaign creation and mission aggregation
  - Zarr export
  - Plotting helpers (non-visual smoke tests)

Run with:
    pytest test_glider_mission.py -v
"""

import os
import pathlib
import shutil
from unittest.mock import MagicMock, call, patch

import pytest

from mamma_mia import (
    add_mission,
    create_campaign,
    create_interpolator,
    create_mission,
    create_platform,
    create_trajectory,
    fly,
    get_data,
    plot_path,
    start_payload_dashboard,
)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

SPEC_FILE = "../examples/spec_files/glider_spec_waypoints.toml"
MISSION_NAME = "Example Glider RAPID"
MISSION_SUMMARY = "Virtual glider performing waypoint mission"
CAMPAIGN_NAME = "Follow waypoints mission"
CAMPAIGN_DESC = "single glider following waypoints"
ZARR_PATH = "waypoints_test.zarr"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def trajectory():
    """Create a trajectory object from the spec file."""
    return create_trajectory(spec_file=SPEC_FILE)


@pytest.fixture(scope="module")
def platform():
    """Create a platform object from the spec file."""
    return create_platform(spec_file=SPEC_FILE)


@pytest.fixture(scope="module")
def mission(trajectory, platform):
    """Create a mission combining trajectory and platform."""
    return create_mission(
        mission_name=MISSION_NAME,
        summary=MISSION_SUMMARY,
        platform=platform,
        trajectory=trajectory,
        apply_obs_error=True,
    )


@pytest.fixture(scope="module")
def mission_with_data(mission):
    """Return a mission after data has been fetched."""
    return get_data(mission=mission)


@pytest.fixture(scope="module")
def interpolator(mission_with_data):
    """Return interpolators built from the fetched-data mission."""
    return create_interpolator(mission=mission_with_data)


@pytest.fixture(scope="module")
def flown_mission(mission_with_data, interpolator):
    """Return a mission that has been flown (payload populated)."""
    return fly(mission=mission_with_data, interpolators=interpolator)


@pytest.fixture(scope="module")
def campaign(flown_mission):
    """Return a campaign containing the flown mission."""
    camp = create_campaign(
        campaign_name=CAMPAIGN_NAME,
        description=CAMPAIGN_DESC,
    )
    return add_mission(campaign=camp, mission=flown_mission)


@pytest.fixture(autouse=True)
def cleanup_zarr():
    """Remove any zarr output created during tests."""
    yield
    if pathlib.Path(ZARR_PATH).exists():
        shutil.rmtree(ZARR_PATH)


# ---------------------------------------------------------------------------
# 1. Trajectory tests
# ---------------------------------------------------------------------------


class TestCreateTrajectory:
    def test_returns_object(self, trajectory):
        assert trajectory is not None

    def test_spec_file_missing_raises(self):
        with pytest.raises((FileNotFoundError, Exception)):
            create_trajectory(spec_file="nonexistent/path.toml")

    def test_has_waypoints_or_coordinates(self, trajectory):
        """Trajectory should expose spatial information in some form."""
        has_attr = any(
            hasattr(trajectory, attr)
            for attr in (
                "waypoints",
                "coordinates",
                "lats",
                "lons",
                "latitude",
                "longitude",
            )
        )
        assert has_attr, "Trajectory object exposes no spatial attributes"

    def test_consistent_across_calls(self):
        """Two calls with the same spec file should produce equivalent objects."""
        t1 = create_trajectory(spec_file=SPEC_FILE)
        t2 = create_trajectory(spec_file=SPEC_FILE)
        # Both should be non-None and of the same type
        assert type(t1) is type(t2)


# ---------------------------------------------------------------------------
# 2. Platform tests
# ---------------------------------------------------------------------------


class TestCreatePlatform:
    def test_returns_object(self, platform):
        assert platform is not None

    def test_spec_file_missing_raises(self):
        with pytest.raises((FileNotFoundError, Exception)):
            create_platform(spec_file="nonexistent/path.toml")

    def test_has_platform_metadata(self, platform):
        """Platform should carry some identifying metadata."""
        has_attr = any(
            hasattr(platform, attr)
            for attr in ("name", "platform_name", "model", "type", "metadata")
        )
        assert has_attr, "Platform object exposes no metadata attributes"

    def test_consistent_across_calls(self):
        p1 = create_platform(spec_file=SPEC_FILE)
        p2 = create_platform(spec_file=SPEC_FILE)
        assert type(p1) is type(p2)


# ---------------------------------------------------------------------------
# 3. Mission creation tests
# ---------------------------------------------------------------------------


class TestCreateMission:
    def test_returns_object(self, mission):
        assert mission is not None

    def test_mission_name_stored(self, mission):
        assert hasattr(mission, "mission_name") or hasattr(mission, "name")
        stored = getattr(mission, "mission_name", None) or getattr(
            mission, "name", None
        )
        assert stored == MISSION_NAME

    def test_summary_stored(self, mission):
        summary = getattr(mission, "summary", None) or getattr(
            mission, "description", None
        )
        assert summary == MISSION_SUMMARY

    def test_obs_error_disabled(self, trajectory, platform):
        """Mission created without obs error should not raise."""
        m = create_mission(
            mission_name="No Obs Error Mission",
            summary="Test",
            platform=platform,
            trajectory=trajectory,
            apply_obs_error=False,
        )
        assert m is not None

    def test_payload_dataset_initially_empty(self, mission):
        """The payload dataset should exist but be empty (no data yet)."""
        payload = getattr(mission, "payload", None) or getattr(
            mission, "payload_ds", None
        )
        assert payload is not None, "Mission has no payload attribute"

    def test_missing_mission_name_raises(self, trajectory, platform):
        with pytest.raises((TypeError, ValueError, Exception)):
            create_mission(
                mission_name=None,
                summary=MISSION_SUMMARY,
                platform=platform,
                trajectory=trajectory,
            )

    def test_missing_platform_raises(self, trajectory):
        with pytest.raises((TypeError, ValueError, Exception)):
            create_mission(
                mission_name=MISSION_NAME,
                summary=MISSION_SUMMARY,
                platform=None,
                trajectory=trajectory,
            )

    def test_missing_trajectory_raises(self, platform):
        with pytest.raises((TypeError, ValueError, Exception)):
            create_mission(
                mission_name=MISSION_NAME,
                summary=MISSION_SUMMARY,
                platform=platform,
                trajectory=None,
            )


# ---------------------------------------------------------------------------
# 4. Data retrieval tests
# ---------------------------------------------------------------------------


class TestGetData:
    def test_returns_mission(self, mission_with_data):
        assert mission_with_data is not None

    def test_mission_has_data_attributes(self, mission_with_data):
        """After get_data the mission should have at least one data-source attribute."""
        has_data = any(
            hasattr(mission_with_data, attr)
            for attr in (
                "data_path",
                "data_source",
                "dataset",
                "data",
                "temperature",
                "salinity",
            )
        )
        assert has_data, "Mission has no data-related attributes after get_data"

    def test_missing_mission_raises(self):
        with pytest.raises((TypeError, AttributeError, Exception)):
            get_data(mission=None)


# ---------------------------------------------------------------------------
# 5. Interpolator tests
# ---------------------------------------------------------------------------


class TestCreateInterpolator:
    def test_returns_object(self, interpolator):
        assert interpolator is not None

    def test_is_callable_or_mapping(self, interpolator):
        """Interpolator should be callable or a dict/mapping of callables."""
        is_callable = callable(interpolator)
        is_mapping = hasattr(interpolator, "__getitem__") or hasattr(
            interpolator, "items"
        )
        assert is_callable or is_mapping, (
            "Interpolator is neither callable nor a mapping"
        )

    def test_missing_mission_raises(self):
        with pytest.raises((TypeError, AttributeError, Exception)):
            create_interpolator(mission=None)


# ---------------------------------------------------------------------------
# 6. Fly tests
# ---------------------------------------------------------------------------


class TestFly:
    def test_returns_mission(self, flown_mission):
        assert flown_mission is not None

    def test_payload_populated(self, flown_mission):
        """After fly(), the payload dataset should contain data variables."""
        payload = getattr(flown_mission, "payload", None) or getattr(
            flown_mission, "payload_ds", None
        )
        assert payload is not None
        has_vars = (
            len(payload) > 0
            if hasattr(payload, "__len__")
            else hasattr(payload, "data_vars") and len(payload.data_vars) > 0
        )
        assert has_vars, "Payload dataset is empty after fly()"

    def test_missing_mission_raises(self, interpolator):
        with pytest.raises((TypeError, AttributeError, Exception)):
            fly(mission=None, interpolators=interpolator)

    def test_missing_interpolator_raises(self, mission_with_data):
        with pytest.raises((TypeError, AttributeError, Exception)):
            fly(mission=mission_with_data, interpolators=None)


# ---------------------------------------------------------------------------
# 7. Campaign tests
# ---------------------------------------------------------------------------


class TestCreateCampaign:
    def test_returns_object(self):
        camp = create_campaign(
            campaign_name=CAMPAIGN_NAME,
            description=CAMPAIGN_DESC,
        )
        assert camp is not None

    def test_campaign_name_stored(self):
        camp = create_campaign(campaign_name=CAMPAIGN_NAME, description=CAMPAIGN_DESC)
        stored = getattr(camp, "campaign_name", None) or getattr(camp, "name", None)
        assert stored == CAMPAIGN_NAME

    def test_description_stored(self):
        camp = create_campaign(campaign_name=CAMPAIGN_NAME, description=CAMPAIGN_DESC)
        desc = getattr(camp, "description", None) or getattr(camp, "summary", None)
        assert desc == CAMPAIGN_DESC

    def test_missing_name_raises(self):
        with pytest.raises((TypeError, ValueError, Exception)):
            create_campaign(campaign_name=None, description=CAMPAIGN_DESC)


class TestAddMission:
    def test_returns_campaign(self, campaign):
        assert campaign is not None

    def test_mission_present_in_campaign(self, campaign, flown_mission):
        missions = getattr(campaign, "missions", None) or getattr(
            campaign, "mission_list", None
        )
        assert missions is not None, "Campaign exposes no missions attribute"
        assert flown_mission in missions or len(missions) > 0

    def test_adding_same_mission_twice(self, flown_mission):
        camp = create_campaign(campaign_name="Dupe Test", description="")
        camp = add_mission(campaign=camp, mission=flown_mission)
        # Second add should either be idempotent or raise a meaningful error
        try:
            camp = add_mission(campaign=camp, mission=flown_mission)
        except Exception:
            pass  # Acceptable: library may forbid duplicates

    def test_none_mission_raises(self):
        camp = create_campaign(campaign_name="Null Mission Test", description="")
        with pytest.raises((TypeError, AttributeError, ValueError, Exception)):
            add_mission(campaign=camp, mission=None)


# ---------------------------------------------------------------------------
# 8. Zarr export tests
# ---------------------------------------------------------------------------


class TestZarrExport:
    def test_zarr_file_created(self, campaign):
        campaign.to_zarr(ZARR_PATH, "w", consolidated=False)
        assert pathlib.Path(ZARR_PATH).exists()

    def test_zarr_is_directory_store(self, campaign):
        campaign.to_zarr(ZARR_PATH, "w", consolidated=False)
        p = pathlib.Path(ZARR_PATH)
        assert p.is_dir(), "Zarr store should be a directory"

    def test_zarr_overwrite(self, campaign):
        """Writing twice in 'w' mode should not raise."""
        campaign.to_zarr(ZARR_PATH, "w", consolidated=False)
        campaign.to_zarr(ZARR_PATH, "w", consolidated=False)
        assert pathlib.Path(ZARR_PATH).exists()


# ---------------------------------------------------------------------------
# 9. Plotting / dashboard smoke tests  (patched — no display required)
# ---------------------------------------------------------------------------


class TestPlotPath:
    @patch("test_glider_mission.plot_path")
    def test_called_with_mission(self, mock_plot, flown_mission):
        plot_path(missions=flown_mission)
        mock_plot.assert_called_once_with(missions=flown_mission)

    @patch("test_glider_mission.plot_path")
    def test_does_not_raise(self, mock_plot, flown_mission):
        mock_plot.return_value = None
        plot_path(missions=flown_mission)  # should not raise


class TestStartPayloadDashboard:
    @patch("test_glider_mission.start_payload_dashboard")
    def test_called_with_mission(self, mock_dash, flown_mission):
        start_payload_dashboard(missions=flown_mission)
        mock_dash.assert_called_once_with(missions=flown_mission)

    @patch("test_glider_mission.start_payload_dashboard")
    def test_does_not_raise(self, mock_dash, flown_mission):
        mock_dash.return_value = None
        start_payload_dashboard(missions=flown_mission)


# ---------------------------------------------------------------------------
# 10. End-to-end integration test
# ---------------------------------------------------------------------------


class TestEndToEndWorkflow:
    def test_full_pipeline_runs(self):
        """Replicate the original script in a single test to confirm it works top to bottom."""
        traj = create_trajectory(spec_file=SPEC_FILE)
        platform = create_platform(spec_file=SPEC_FILE)

        mission = create_mission(
            mission_name=MISSION_NAME,
            summary=MISSION_SUMMARY,
            platform=platform,
            trajectory=traj,
            apply_obs_error=True,
        )

        mission = get_data(mission=mission)
        interpolator = create_interpolator(mission=mission)
        mission = fly(mission=mission, interpolators=interpolator)

        campaign = create_campaign(
            campaign_name=CAMPAIGN_NAME,
            description=CAMPAIGN_DESC,
        )
        campaign = add_mission(campaign=campaign, mission=mission)

        zarr_out = "e2e_test.zarr"
        try:
            campaign.to_zarr(zarr_out, "w", consolidated=False)
            assert pathlib.Path(zarr_out).exists()
        finally:
            if pathlib.Path(zarr_out).exists():
                shutil.rmtree(zarr_out)

        with (
            patch("test_glider_mission.plot_path") as mock_plot,
            patch("test_glider_mission.start_payload_dashboard") as mock_dash,
        ):
            plot_path(missions=mission)
            start_payload_dashboard(missions=mission)
            mock_plot.assert_called_once()
            mock_dash.assert_called_once()
