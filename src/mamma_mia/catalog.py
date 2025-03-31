from attrs import define, field
import intake
import copernicusmarine
from loguru import logger

# TODO find a better way to do this, MSM sources use meta data in intake catalog.
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


@define
class Cats:
    """
    Catalog class, contains all the model source data that is available to download. There is a field for each source,
    these are populated with their relevent catalogs that can be searched for matching worlds.

    Args:
        search: string that overrides the default search term used for CMEMS sources
        cat_path: string that overides the default catalog location used for MSM sources
        overwrite: bool that overwrites the metadata cache used for CMEMS sources

    Returns:
        Populated Cats object
    """
    cmems_cat: dict = field(factory=dict)
    msm_cat: intake.Catalog = field(factory=intake.Catalog)
    search : str = "Global"
    cat_path: str = "https://noc-msm-o.s3-ext.jc.rl.ac.uk/mamma-mia/catalog/catalog.yml"
    overwrite: bool = False
    sources: dict = {"CMEMS": 1 ,"MSM" : 2 }

    def __attrs_post_init__(self):
        self.cmems_cat = copernicusmarine.describe(contains=[self.search], include_datasets=True,overwrite_metadata_cache=self.overwrite)
        self.msm_cat = intake.open_catalog(self.cat_path)

    def get_sources_list(self):
        """
        list of model sources that can be downloaded to use within Mamma Mia along with their priority
        Returns: list of available world sources

        """
        return self.sources

    def set_priority(self, source:str,priority:int):
        """
        Sets the priority of a given source
        Returns:

        """
        self.sources[source] = priority
        logger.success(f"Set priority of {source} to {priority}")