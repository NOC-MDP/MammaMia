import bpy
import csv

def create_curve(coords_list):
    crv = bpy.data.curves.new('crv', 'CURVE')
    crv.dimensions = '3D'
    spline = crv.splines.new(type='NURBS')
    spline.points.add(len(coords_list) - 1) 
    for p, new_co in zip(spline.points, coords_list):
        p.co = (new_co + [1.0])
    obj = bpy.data.objects.new('object_name', crv)
    bpy.data.scenes[0].collection.objects.link(obj)

coords_list = []
with open('/Users/thopri/MammaMia/track.csv') as csv_file:
    csv_reader= csv.reader(csv_file,delimiter=',')
    for row in csv_reader:
        coords_list.append([float(row[0]),float(row[1]),float(row[2])])



create_curve(coords_list)