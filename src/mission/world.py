from pyinterp import RTree
import zarr


class World(zarr.Group):
    def __init__(self, path:str):
        store = zarr.DirectoryStore(path=path)
        # Create the group using the separate method
        group = zarr.open_group(store=store)
        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=True, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)
        # Add any additional initialization here
        self.spatial_tree = RTree()

    def build_tree(self):
        print(f"would be building tree here at {self.spatial_tree}")
