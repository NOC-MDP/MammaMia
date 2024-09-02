import intake

cat = intake.open_catalog('src/mission/catalog.yml')

print(list(cat))

data = cat.eORCA12_201908.to_dask()
print(data)
print("the end")

