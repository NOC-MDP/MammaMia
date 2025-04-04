from attrs import define, field
import intake
import copernicusmarine
from loguru import logger

# TODO move this to the parameter json file to a field called world_aliases
# Aliases used to map CMEMS variable names to Mamma Mia parameter names
cmems_alias = {
    "nitrate": ["no3"],
    "phosphate": ["po4"],
    "silicate": ["si"],
    "TEMP": ["thetao"],
    "CNDC": ["so"],
    "PRES": ["pres"],
    "WATERCURRENTS_U": ["uo"],
    "WATERCURRENTS_V": ["vo"],
    "WATERCURRENTS_W": ["wo"]
}

# Aliases used to map model field type to CMEMS dataset name
model_field_alias = {"monthly_means": ["P1M-m"],
                     "daily_means": ["P1D-m"],
                     "6_hours_instant": ["PT6H-i"],
                     }
# set preferred order of model field data
field_rank_order = ["6_hours_instant", "daily_means","monthly_means"]
field_rank_map = {key: i for i, key in enumerate(field_rank_order)}

@define
class Cats:
    """
    Catalog class, contains all the model source data that is available to download. There is a field for each source,
    these are populated with their relevant catalogs that can be searched for matching worlds.

    Args:
        search: string that overrides the default search term used for CMEMS sources
        cat_path: string that overrides the default catalog location used for MSM sources
        overwrite: bool that overwrites the metadata cache used for CMEMS sources

    Returns:
        Populated Cats object
    """
    cmems_cat: dict = field(factory=dict)
    msm_cat: intake.Catalog = field(factory=intake.Catalog)
    search: str = "Global"
    cat_path: str = "https://noc-msm-o.s3-ext.jc.rl.ac.uk/mamma-mia/catalog/catalog.yml"
    overwrite: bool = False
    sources: dict = {"CMEMS": 1, "MSM": 2}

    def init_catalog(self):
        self.cmems_cat = copernicusmarine.describe(contains=[], include_datasets=True,
                                                   overwrite_metadata_cache=self.overwrite)
        self.msm_cat = intake.open_catalog(self.cat_path)

    def get_sources_list(self):
        """
        list of model sources that can be downloaded to use within Mamma Mia along with their priority
        Returns: list of available world sources

        """
        return self.sources

    def set_priority(self, source: str, priority: int):
        """
        Sets the priority of a given source
        Returns:

        """
        self.sources[source] = priority
        logger.success(f"Set priority of {source} to {priority}")
